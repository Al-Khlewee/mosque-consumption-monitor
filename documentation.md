# 📚 Documentation - Mosque Consumption Monitoring System

## 1. System Architecture Summary

The **Mosque Consumption Monitoring System** is a lightweight, web-based application designed to validate the feasibility of monitoring and forecasting resource usage in mosques.

### **Tech Stack:**
*   **Database**: **SQLite**. Chosen for its simplicity, serverless nature, and ease of setup for a POC. It manages three core entities: `Mosques`, `Meters`, and `Consumption Readings`.
*   **Backend/Data Processing**: **Python** with **Pandas**. Used for robust data manipulation, aggregation (e.g., monthly sums), and preparing data for the frontend.
*   **Frontend**: **Streamlit**. Selected for its rapid development capabilities, allowing the creation of interactive data dashboards and forms entirely in Python without needing separate HTML/CSS/JS.
*   **Forecasting Engine**: **Scikit-Learn (Linear Regression)**. Integrated directly into the application flow to provide real-time predictions.
*   **Visualization**: **Plotly**. used to generate interactive, responsive charts with full Arabic language support.

### **Data Flow:**
1.  User inputs reading (or script generates data) -> Saved to `SQLite`.
2.  User requests Dashboard -> Python queries `SQLite` -> `Pandas` processes data -> `Plotly` visualizes it in `Streamlit`.
3.  User requests Forecast -> `Pandas` prepares historical series -> `Scikit-Learn` trains model -> Predictions displayed.

---

## 2. Algorithm Choice: Linear Regression

For the Forecasting Module, we selected **Linear Regression** for this Proof of Concept.

### **Why Linear Regression?**
1.  **Speed & Efficiency**: The requirement specified forecasting must be fast (< 10 seconds). Linear regression is computationally inexpensive and trains instantaneously on datasets of this size (< 10,000 records).
2.  **Trend Detection**: It is excellent at identifying the general upward or downward trend in consumption over time.
3.  **Simplicity & Interpretability**: It provides a clear baseline. For a manager, understanding that "consumption is increasing by X units per day on average" is often more actionable than complex "black box" outputs.
4.  **POC Suitability**: Given the dummy data has clear, programmable seasonality and trends, Linear Regression (especially when mapped with time features) captures the core signal effectively without the overhead of tuning complex hyperparameters required by ARIMA or LSTM.

*Start simple, then iterate. Future versions could use **Facebook Prophet** to better capture complex multiple seasonalities (weekly vs yearly).*

---

## 3. User Manual: Data Entry

### **How to Add a New Meter Reading**

**Role**: Mosque Manager / Admin

1.  **Navigation**:
    *   Open the application sidebar (click the `>` arrow at the top left if closed).
    *   Click on **"إدخال البيانات" (Data Entry)**.

2.  **Fill the Form**:
    *   **اختر المسجد (Select Mosque)**: Choose the mosque you are updating from the dropdown list.
    *   **اختر العداد (Select Meter)**: Choose the specific meter (Observation: The list filters automatically based on the selected mosque).
    *   **تاريخ القراءة (Reading Date)**: Pick the date of the reading. It defaults to today.
    *   **قراءة العداد الحالية (Current Reading)**: Enter the value shown on the physical meter.
    *   **كمية الاستهلاك (Consumption Amount)**: Enter the consumption since the last reading.
        *   *Tip: If you have the previous reading, this is (Current - Previous).*

3.  **Submit**:
    *   Click the **"حفظ القراءة" (Save Reading)** button.
    *   You will see a green success message **"تم حفظ البيانات بنجاح!"** if the system accepted the data.

4.  **Verify**:
    *   Go to the **Dashboard** page to see your new data reflected in the charts immediately.

---

## 4. How to Run the App
Open your terminal in `c:\Users\hatem\Desktop\POWERC\` and run:
```bash
python -m streamlit run app.py
```
