from flask import Flask, render_template, request, jsonify
import joblib
import pandas as pd
import numpy as np
import plotly.graph_objs as go
import plotly.offline as pyo
import json
import os
from datetime import datetime

app = Flask(__name__)

# Load the trained model
MODEL_PATH = os.path.join("mental_health_prediction_model.pkl")

try:
    model_components = joblib.load(MODEL_PATH)
    model = model_components["model"]
    scaler = model_components["scaler"]
    label_encoders = model_components["label_encoders"]
    feature_columns = model_components["feature_columns"]
    model_name = model_components["model_name"]
    scaled_algorithms = ["Logistic Regression", "Linear SVM", "KNN"]
    print(f"✅ Model loaded successfully: {model_name}")
except Exception as e:
    print(f"❌ Error loading model: {e}")
    model = None

def preprocess_input(form_data):
    """Preprocess form data for model prediction"""
    try:
        # Create dataframe from form data
        data_dict = {}
        for col in feature_columns:
            data_dict[col] = form_data.get(col, 'Unknown')
        
        df = pd.DataFrame([data_dict])
        
        # Apply label encoding
        for col in feature_columns:
            if col in label_encoders and col in df.columns:
                value = df[col].iloc[0]
                if value in label_encoders[col].classes_:
                    df[col] = label_encoders[col].transform([value])[0]
                else:
                    df[col] = 0  # Default value for unknown categories
        
        # Scale if needed
        if model_name in scaled_algorithms:
            return scaler.transform(df)
        else:
            return df.values
            
    except Exception as e:
        print(f"Preprocessing error: {e}")
        return None

def create_visualizations(prediction, confidence, risk_factors):
    """Create interactive visualizations using Plotly"""
    
    # 1. Confidence Gauge Chart
    gauge_fig = go.Figure(go.Indicator(
        mode = "gauge+number+delta",
        value = confidence * 100,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': "Prediction Confidence (%)"},
        delta = {'reference': 80},
        gauge = {
            'axis': {'range': [None, 100]},
            'bar': {'color': "#1f77b4"},
            'steps': [
                {'range': [0, 50], 'color': "lightgray"},
                {'range': [50, 80], 'color': "yellow"},
                {'range': [80, 100], 'color': "lightgreen"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 90
            }
        }
    ))
    gauge_fig.update_layout(height=300, font={'color': "darkblue", 'family': "Arial"})
    gauge_html = gauge_fig.to_html(full_html=False, include_plotlyjs='cdn')
    
    # 2. Risk Factors Bar Chart
    risk_names = list(risk_factors.keys())
    risk_values = list(risk_factors.values())
    colors = ['#ff6b6b' if v > 70 else '#feca57' if v > 40 else '#48dbfb' for v in risk_values]
    
    bar_fig = go.Figure(data=[
        go.Bar(x=risk_names, y=risk_values, marker_color=colors)
    ])
    bar_fig.update_layout(
        title="Risk Factor Analysis",
        xaxis_title="Risk Factors",
        yaxis_title="Risk Level (%)",
        height=400,
        font={'color': "darkblue", 'family': "Arial"}
    )
    bar_html = bar_fig.to_html(full_html=False, include_plotlyjs=False)
    
    # 3. Treatment Recommendation Pie Chart
    treatment_prob = confidence if prediction == 1 else 1 - confidence
    no_treatment_prob = 1 - treatment_prob
    
    pie_fig = go.Figure(data=[go.Pie(
        labels=['Treatment Recommended', 'No Treatment Needed'],
        values=[treatment_prob * 100, no_treatment_prob * 100],
        hole=.3,
        marker_colors=['#ff6b6b', '#48dbfb']
    )])
    pie_fig.update_layout(
        title="Treatment Recommendation",
        height=400,
        font={'color': "darkblue", 'family': "Arial"}
    )
    pie_html = pie_fig.to_html(full_html=False, include_plotlyjs=False)
    
    return gauge_html, bar_html, pie_html

def generate_suggestions(prediction, confidence, form_data):
    """Generate personalized mental health suggestions"""
    suggestions = []
    
    if prediction == 1:  # Treatment recommended
        suggestions.extend([
            "🏥 **Immediate Action**: Consider consulting a licensed mental health professional",
            "📞 **Crisis Support**: Keep emergency helpline numbers readily available",
            "👥 **Support System**: Reach out to trusted friends, family, or support groups",
            "📋 **Professional Help**: Schedule an appointment with a psychiatrist or psychologist"
        ])
    
    # Specific suggestions based on form responses
    if form_data.get('Growing_Stress') == 'Yes':
        suggestions.extend([
            "🧘 **Stress Management**: Practice daily meditation or deep breathing exercises",
            "💪 **Physical Activity**: Engage in regular exercise (30 minutes, 5 times/week)",
            "⏰ **Time Management**: Use stress-reduction techniques like time blocking"
        ])
    
    if form_data.get('Social_Weakness') == 'Yes':
        suggestions.extend([
            "🤝 **Social Connection**: Join community groups or hobby-based meetups",
            "💬 **Communication**: Practice social skills in low-pressure environments",
            "🌐 **Online Communities**: Participate in supportive online forums"
        ])
    
    if form_data.get('Coping_Struggles') == 'Yes':
        suggestions.extend([
            "📝 **Journaling**: Maintain a daily mood and thought journal",
            "🎨 **Creative Outlets**: Explore art, music, or writing as coping mechanisms",
            "🧠 **Coping Skills**: Learn and practice healthy coping strategies"
        ])
    
    if form_data.get('Work_Interest') == 'No':
        suggestions.extend([
            "🎯 **Goal Setting**: Set small, achievable daily goals",
            "🔄 **Routine**: Establish a consistent daily routine",
            "🏆 **Achievement**: Celebrate small accomplishments"
        ])
    
    # General wellness suggestions
    suggestions.extend([
        "😴 **Sleep Hygiene**: Maintain 7-9 hours of quality sleep nightly",
        "🥗 **Nutrition**: Eat a balanced diet rich in omega-3s and vitamins",
        "☀️ **Sunlight**: Get 15-30 minutes of sunlight exposure daily",
        "📱 **Digital Detox**: Limit social media and screen time before bed"
    ])
    
    return suggestions[:10]  # Return top 10 suggestions

def calculate_risk_factors(form_data):
    """Calculate risk factors based on form data"""
    risk_factors = {}
    
    # Stress Level
    stress_indicators = ['Growing_Stress', 'Changes_Habits', 'Coping_Struggles']
    stress_score = sum([50 for indicator in stress_indicators if form_data.get(indicator) == 'Yes'])
    risk_factors['Stress Level'] = min(stress_score, 100)
    
    # Social Factors
    social_score = 0
    if form_data.get('Social_Weakness') == 'Yes':
        social_score += 40
    if form_data.get('mental_health_interview') == 'No':
        social_score += 30
    risk_factors['Social Support'] = min(social_score, 100)
    
    # Work/Life Balance
    work_score = 0
    if form_data.get('Work_Interest') == 'No':
        work_score += 50
    if form_data.get('self_employed') == 'Yes':
        work_score += 20
    risk_factors['Work-Life Balance'] = min(work_score, 100)
    
    # Family History
    family_score = 60 if form_data.get('family_history') == 'Yes' else 20
    risk_factors['Genetic Factors'] = family_score
    
    # Mental Health History
    history_score = 70 if form_data.get('Mental_Health_History') == 'Yes' else 15
    risk_factors['Mental Health History'] = history_score
    
    return risk_factors

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/prediction')
def prediction():
    return render_template('prediction.html')

@app.route('/resources')
def resources():
    return render_template('resources.html')

@app.route('/predict', methods=['POST'])
def predict():
    try:
        if not model:
            return render_template('result.html', error="Model not loaded properly")
        
        form_data = request.form.to_dict()
        
        # Preprocess the data
        processed_data = preprocess_input(form_data)
        if processed_data is None:
            return render_template('result.html', error="Error processing input data")
        
        # Make prediction
        prediction = int(model.predict(processed_data)[0])
        
        # Get confidence score
        if hasattr(model, 'predict_proba'):
            probabilities = model.predict_proba(processed_data)[0]
            confidence = float(max(probabilities))
        else:
            confidence = 0.85  # Default confidence
        
        # Calculate risk factors
        risk_factors = calculate_risk_factors(form_data)
        
        # Create visualizations
        gauge_chart, bar_chart, pie_chart = create_visualizations(prediction, confidence, risk_factors)
        
        # Generate suggestions
        suggestions = generate_suggestions(prediction, confidence, form_data)
        
        # Prepare result data
        result_data = {
            'prediction': prediction,
            'confidence': confidence,
            'model_name': model_name,
            'treatment_needed': "Yes" if prediction == 1 else "No",
            'risk_level': "High" if confidence > 0.8 else "Medium" if confidence > 0.6 else "Low",
            'gauge_chart': gauge_chart,
            'bar_chart': bar_chart,
            'pie_chart': pie_chart,
            'suggestions': suggestions,
            'risk_factors': risk_factors
        }
        
        return render_template('result.html', **result_data)
        
    except Exception as e:
        print(f"Prediction error: {e}")
        return render_template('result.html', error=f"An error occurred: {str(e)}")

@app.context_processor
def inject_now():
    return {'now': datetime.utcnow}

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
