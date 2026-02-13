# 🌾 Zarai Radar - Agricultural Advisory Platform

**Zarai Radar** is a comprehensive, AI-driven agricultural decision support system designed specifically for farmers in Pakistan. It combines real-time weather data, machine learning-based disease detection, and expert agricultural knowledge to provide personalized, actionable insights that help farmers maximize yield while minimizing resource waste.

---

## 🎯 Project Overview

Zarai Radar transforms complex agricultural data into simple, farmer-friendly recommendations. The platform integrates multiple data sources and AI technologies to deliver:

- **Hyper-local weather forecasting** (down to individual farm coordinates)
- **Precision fertilizer recommendations** based on crop stage, soil type, and yield targets
- **Smart irrigation scheduling** that adapts to weather patterns and crop water needs
- **AI-powered disease detection** using computer vision (TensorFlow/Keras)
- **Early risk assessment** combining rule-based logic with RAG (Retrieval-Augmented Generation)
- **Bilingual support** (English and Urdu) for accessibility

---

## 🏗️ System Architecture

### **Frontend** (Next.js 15 + React)
- **Github**: [Frontend](https://github.com/Furqan7313/agri-tech)
- **Location**: `agri-tech/`
- **Framework**: Next.js with TypeScript
- **Styling**: Tailwind CSS with custom design system
- **State Management**: React Context API
- **UI Components**: Radix UI + shadcn/ui
- **Key Features**:
  - Responsive, mobile-first design
  - Real-time dashboard with live weather updates
  - Interactive chat interface with AI assistant
  - Disease prediction image upload interface
  - Bilingual UI (English/Urdu)

### **Backend** (FastAPI + Python)
- **Location**: `App/`
- **Framework**: FastAPI (async Python web framework)
- **Database**: Supabase (PostgreSQL with pgvector for semantic search)
- **Authentication**: JWT-based token authentication
- **Key Services**:
  - Weather data aggregation (OpenWeather + Open-Meteo APIs)
  - Fertilizer calculation engine
  - Irrigation advisory system
  - Disease prediction service (TensorFlow/Keras)
  - RAG-based agricultural knowledge assistant

### **AI/ML Components**
1. **Disease Classification Model**
   - **Technology**: TensorFlow/Keras CNN
   - **Classes**: Brown Rust, Yellow Rust, Healthy
   - **Preprocessing**: Color-based segmentation (HSV masking)
   - **Deployment**: Lazy-loaded to optimize server startup time

2. **RAG Knowledge System**
   - **Location**: `RAG/`
   - **Technology**: LangChain + Google Gemini + Sentence Transformers
   - **Knowledge Base**: Curated agricultural research (wheat diseases, climate risks, best practices)
   - **Vector Store**: Supabase pgvector for semantic search
   - **Hybrid Approach**: Combines rule-based filtering with semantic retrieval

---

## 🚀 Key Features & How They Work

### 1. **Hyper-Local Weather Intelligence**

**How it works:**
- Farmers provide thier specific district information to get the updated weather data
- Data sources:
  - **OpenWeather API**: Current conditions (temperature, humidity, wind)
  - **Open-Meteo API**: 7-day forecast with hourly granularity
- **Caching**: 15-minute TTL to reduce API calls and improve response time

---

### 2. **Precision Fertilizer Recommendations**

**How it works:**

#### **Step 1: Base Calculation**
- Adjusts Nitrogen based on target yield (e.g., +10kg N per 10 maunds increase)

#### **Step 2: Environmental Adjustments**
- **Soil Type Multipliers**:
  - Sandy soil: +20% Nitrogen (faster leaching)
  - Clay soil: +15% Phosphorus (harder root penetration)
- **Irrigation Type**:
  - Rainfed: -10% to prevent salt buildup
  - Tube Well: Standard rates

#### **Step 3: Split Scheduling**
- Divides fertilizer into growth-stage-specific applications:
  - **Sowing**: 30% N + 100% P + 100% K
  - **Tillering**: 40% N
  - **Jointing**: 30% N
- Marks each application as `DUE_NOW`, `UPCOMING`, or `MISSED` based on days after sowing

#### **Step 4: Product Conversion**
- Converts nutrient weights (kg) to actual market products:
  - DAP (Diammonium Phosphate) for Phosphorus
  - Urea for remaining Nitrogen
  - MOP (Muriate of Potash) for Potassium
- Calculates exact bag quantities and costs

#### **Step 5: Weather-Aware Tips**
- If heavy rain (>30mm) is forecasted: "⚠️ Delay application by 2-3 days"
- If critical stage missed: "❗ MISSED Tillering Application - Consult expert"

---

### 3. **Smart Irrigation Advisory**

**How it works:**

#### **Growth Stage Detection**
- Maps days after sowing (DAS) to physiological stages:
  - 0-14 days: Germination
  - 15-35 days: Tillering
  - 36-55 days: Jointing
  - 56-75 days: Booting
  - 76-110 days: Flowering
  - 111-140 days: Grain Filling

#### **Water Requirement Calculation**
- Base requirement (mm/day) varies by stage (e.g., 5mm during Flowering)
- Adjustments:
  - **Temperature**: +0.5mm per degree above 25°C
  - **Humidity**: -0.3mm per 10% above 60%
  - **Recent Rain**: Subtracts rainfall from last 3 days

#### **Irrigation Scheduling**
- Converts water depth (mm) to volume (liters) based on farm area
- Provides next irrigation date based on depletion rate
- Warns if soil moisture is critically low

---

### 4. **AI Disease Detection**

**How it works:**

#### **Image Preprocessing**
1. User uploads wheat leaf image
2. **Color Segmentation** (HSV-based):
   - Brown Rust: HSV range [10-30, 45-255, 45-255]
   - Yellow Rust: HSV range [20-35, 100-255, 100-255]
   - Healthy: HSV range [35-85, 40-255, 40-255]
3. Applies mask to isolate disease-relevant regions
4. Resizes to 224x224 pixels

#### **Model Inference**
- **Architecture**: Custom CNN (VGG16-inspired)
- **Input**: 224x224 RGB image
- **Output**: 3-class probability distribution
- **Confidence**: Softmax probability × 100

#### **Lazy Loading**
- Model is NOT loaded during server startup
- First prediction request triggers model load (~5-10 seconds)
- Subsequent predictions are instant (model stays in memory)

---

### 5. **Early Risk Assessment**

**How it works:**

#### **Phase 1: Rule-Based Filtering**
- Scans knowledge base for diseases/risks matching:
  - Current crop stage
  - Days after sowing range
  - Temperature thresholds
  - Humidity conditions
- Calculates risk score (0-100) based on condition match quality

#### **Output**
- **Disease Risk**: List of likely diseases with severity and treatment
- **Climate Risk**: Active threats (frost, heat stress, drought)
- **Priority Actions**: Top 2-3 immediate steps to take

---

---

## 📦 Installation & Setup

### **Prerequisites**
- Python 3.10+
- Node.js 18+
- Supabase account
- API Keys:
  - OpenWeather API
  - Google Gemini API
  - Supabase URL + Key

### **Backend Setup**

```bash
# Navigate to project root
cd "e:\Python\GEN AI\Zarai Radar"

# Create virtual environment
python -m venv zarai_env
.\zarai_env\Scripts\Activate.ps1  # Windows
# source zarai_env/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Add your API keys to .env

# Run database migrations (Supabase SQL Editor)
# Execute the SQL in App/db/schema.sql

# Start backend server
uvicorn App.app:app --reload --host 0.0.0.0 --port 8000
```

### **Frontend Setup**

```bash
# Navigate to frontend directory
cd agri-tech

# Install dependencies
npm install

# Create .env.local file
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local

# Start development server
npm run dev
```


## 📊 Technology Stack

### **Frontend**
- Next.js 15 (React 19)
- TypeScript
- Tailwind CSS
- Radix UI / shadcn/ui
- Lucide Icons

### **Backend**
- FastAPI
- Python 3.12+
- Supabase (PostgreSQL + pgvector)
- Pydantic (data validation)

### **AI/ML**
- TensorFlow / Keras (disease detection)
- LangChain (RAG orchestration)
- Google Gemini (LLM)
- Sentence Transformers (embeddings)
- OpenCV (image preprocessing)

### **APIs**
- OpenWeather (current weather)
- Open-Meteo (forecasts)
- Google Maps (location services)

---

## 📁 Project Structure

```
zarai-radar/
├── agri-tech/                    # Next.js Frontend
│   ├── src/
│   │   ├── app/                  # Pages (landing, dashboard, setup, login)
│   │   ├── components/           # React components
│   │   │   ├── dashboard/        # Dashboard widgets
│   │   │   ├── landing/          # Landing page sections
│   │   │   ├── chat/             # Chat interface
│   │   │   └── ui/               # shadcn/ui components
│   │   ├── context/              # React Context (AgriContext)
│   │   └── lib/                  # Utilities (API client, i18n)
│   └── public/                   # Static assets
│
├── App/                          # FastAPI Backend
│   ├── routes/                   # API endpoints
│   │   ├── auth.py               # Authentication
│   │   ├── dashboard.py          # Dashboard data
│   │   ├── farmer.py             # Farmer profile
│   │   └── prediction.py         # Disease prediction
│   ├── services/                 # Business logic
│   │   ├── climate.py            # Weather data
│   │   └── prediction.py         # ML inference
│   ├── data/                     # Domain logic
│   │   ├── fertilizer_recommendation.py
│   │   ├── irrigation.py
│   │   ├── seasonal_guaidness.py
│   │   └── fertilizer_knowledge_base.json
│   ├── schema/                   # Pydantic models
│   └── db.py                     # Supabase client
│
├── RAG/                          # AI Knowledge System
│   ├── orchestrator.py           # LangGraph agent
│   ├── hybrib_assess.py          # Hybrid risk assessment
│   ├── data/
│   │   └── wheat_knowledge_base.json
│   └── ingest.py                 # Vector embedding ingestion
│
├── requirements.txt              # Python dependencies
└── README.md                     # This file
```

---

## 🌟 Future Enhancements

- [ ] Interactive Google Maps integration for farm location selection
- [ ] Satellite imagery analysis (NDVI, soil moisture)
- [ ] Multi-crop support (rice, cotton, sugarcane)
- [ ] SMS-based alerts for low-literacy farmers
- [ ] Marketplace integration for fertilizer/seed purchasing
- [ ] Yield prediction using historical data
- [ ] Community forum for farmer-to-farmer knowledge sharing

---

## 👥 Contributors

- **Abdul Wahab** - AI & Backend Developer
- **Furqan** - Frontend Developer

---

## 📄 License

This project is licensed under the MIT License.

---

## 🙏 Acknowledgments

- **PARC (Pakistan Agricultural Research Council)** - Fertilizer guidelines
- **Punjab Agriculture Department** - Crop calendars and best practices
- **Open-Meteo & OpenWeather** - Weather data APIs
- **Grok** - AI language model
- **Supabase** - Database and vector storage

---

## 📞 Support

For issues or questions, please open an issue on GitHub or contact the development team.

**Built with ❤️ for Pakistani farmers**
