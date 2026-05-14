# 🧾 SmartSplit Bill AI

SmartSplit Bill AI is an intelligent, user-friendly Streamlit application designed to take the hassle out of splitting restaurant bills among friends. Simply upload a photo of your receipt, and the app will automatically extract all line items, taxes, and service charges, allowing you to assign who ate what and instantly calculate everyone's fair share.

## ✨ Features

- **🤖 AI-Powered Extraction:** Uses **Gemini 2.5 Flash** to highly accurately parse receipt images into structured data.
- **📷 Offline OCR Fallback:** Don't want to use an API key? Use the built-in offline extraction powered by **EasyOCR** (no internet required).
- **📝 Fully Editable Table:** Mistakes happen. You can easily edit item names, quantities, and prices directly in the app.
- **👥 Smart Item Assignment:** An intuitive checkbox grid lets you assign multiple people to a single item—the app splits the cost of that item equally among them.
- **🧮 Fair Tax & Service Splitting:** Taxes, service charges, and discounts are distributed proportionally based on each person's subtotal.
- **💾 Export to CSV:** Download the final breakdown as a CSV file for your records or to share with friends.

## 🚀 Getting Started

### Prerequisites
- Python 3.9 or higher
- Git

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/username/Smart_splitbill.git
   cd Smart_splitbill
   ```

2. **Create and activate a virtual environment (Recommended):**
   ```bash
   python -m venv venv
   
   # Windows:
   venv\Scripts\activate
   # Mac/Linux:
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up your API Key:**
   - Copy the `.env.example` file and rename it to `.env`:
     ```bash
     cp .env.example .env
     ```
   - Get a free Gemini API key from [Google AI Studio](https://aistudio.google.com/).
   - Open `.env` and paste your API key:
     ```env
     GEMINI_API_KEY=your_gemini_api_key_here
     ```

## 🎮 How to Run

Start the Streamlit application by running:
```bash
streamlit run app.py
```
The application will automatically open in your default web browser at `http://localhost:8501`.

## 🛠️ Built With

- [Streamlit](https://streamlit.io/) - The web framework used for the UI
- [Google Gemini API](https://ai.google.dev/) - For advanced receipt parsing
- [EasyOCR](https://github.com/JaidedAI/EasyOCR) - For offline Optical Character Recognition
- [Pandas](https://pandas.pydata.org/) - For data manipulation and dynamic tables

## 📝 License

This project is open-source and available under the [MIT License](LICENSE).

## LINK
https://smartsplitbill.streamlit.app/
