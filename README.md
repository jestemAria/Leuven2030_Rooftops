# Leuven2030_Rooftops


Leuven2030_Rooftops/

├── webapp-with-two-pages.py                <-- main page

├── pages/                   <-- new folder

│   ├── 01_Top_200_Priorities.py  <-- (Hang's data)

│   └── 02_Full_City_Scan.py      <-- (Ha Van/Alex's 56k data)

└── ...


streamlit run webapp-with-two-pages.py



☀️ Leuven 2030 Solar Rooftop Analyzer

A data-driven decision support tool designed to prioritize large-scale solar installations in Leuven. This project combines WFS Geospatial Data, PVGIS Solar Estimates, and Computer Vision (AI) to identify the most promising rooftops for green energy transition.

🚀 Key Features

Interactive Map: Visualize Leuven's building footprints with dual-layer rendering (Candidates vs. Top 200).

AI-Powered Classification: Automatically distinguishes between Flat and Pitched roofs using Deep Learning (ResNet-18) on satellite imagery.

Smart Filtering: Filter buildings by Area, CO₂ Reduction Potential, Orientation, and Roof Type.

Data Integration: Merges geometry, energy estimates, and address data into a unified view.

🛠️ Installation

Prerequisites

Python 3.9 or higher

(Optional) QGIS for viewing .gpkg files manually.

1. Clone the Repository

git clone [https://github.com/YourUsername/Leuven2030_Rooftops.git](https://github.com/YourUsername/Leuven2030_Rooftops.git)
cd Leuven2030_Rooftops


2. Install Dependencies

This project relies on geospatial and deep learning libraries.

pip install -r requirements.txt


Note: If you encounter issues installing geopandas or rasterio on Windows, consider using pre-built binaries (conda) or WSL.

🏃‍♂️ How to Run the Web App

To launch the dashboard locally:

streamlit run webapp-with-two-pages.py


The app will open in your browser at http://localhost:8501.

🧠 How to Run the AI Pipeline

The AI module fetches satellite images and classifies rooftops. Follow these steps to reproduce the AI results:

Step 1: Prepare Data

Ensure the source geospatial file exists at:
notebooks/data/large_roofs_test.gpkg

Step 2: Training (Optional)

If you want to re-train the model with new labels:

cd notebooks
python train_classifier.py


This will generate a rooftop_classifier_resnet18.pth model file.

Step 3: Inference (Prediction)

To run the model on the full dataset and generate tags:

cd notebooks
python predict_rooftypes.py


Output: This will create notebooks/data/200_large_with_pv_enriched.gpkg, which is automatically picked up by the Streamlit app.

📂 Project Structure

Leuven2030_Rooftops/
├── webapp.py                  # Main Entry Point
├── pages/
│   ├── 01_Top_200_Priorities.py  # Main Dashboard (AI + PVGIS Data)
│   └── 02_Full_City_Map.py       # Overview of 56k buildings
├── notebooks/
│   ├── data/                  # GeoPackage & CSV Data files
│   ├── rooftop_dataset.py     # AI: Data Ingestion & WMS Fetching
│   ├── train_classifier.py    # AI: Model Training Script
│   ├── predict_rooftypes.py   # AI: Inference Script
│   └── ...                    # Jupyter Notebooks for data scraping
└── requirements.txt           # Python Dependencies


🤝 Contribution

Data Engineering: WFS extraction and Geometry processing.

Solar Modeling: PVGIS integration and potentiality calculation.

AI & Frontend: Computer Vision pipeline and Streamlit App development.

Built for the Emergent Leuven consulting project for Leuven 2030.
