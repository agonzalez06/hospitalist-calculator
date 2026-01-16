# Hospitalist Compensation Calculator

Web-based compensation calculator for hospitalists using the A+B Component salary model.

**Fiscal Year:** July 1, 2026 - June 30, 2027

## Live Demo

[View the calculator on Streamlit Cloud](https://hospitalist-calculator.streamlit.app) *(Update this URL after deployment)*

## Features

- **FTE Allocation**: Input status FTE, non-clinical time, and departmental allocations
- **Shift Mix Builder**: Configure teaching, direct care, nights, and specialty shifts
- **Real-time Calculation**: See compensation update instantly as you adjust inputs
- **Transparent Breakdown**: View detailed A and B component calculations

## Compensation Model

### A Component (Base Salary)
Fixed by academic rank:
- Assistant Professor: $105,000
- Associate Professor: $115,000
- Professor: $125,000

### B Component (Strength of Schedule)
Calculated from shift mix:

| Shift Type | Shift Ratio | SoS Value |
|------------|-------------|-----------|
| Teaching | 1.0 | 1.0 |
| Direct Care Days | 1.0 | 1.25 |
| Women & Families | 1.2 | 1.25 |
| Standard Nights (first 21) | 1.0 | 1.5 |
| Premium Nights (after 21) | 1.0 | 1.75 |
| Episcopal | 0.75 | 1.05 |
| MVP Clinic | 0.9 | 1.125 |

**Base:** 1.0 FTE = 183 shift equivalents/year
**Experience:** +$2,000 per year since residency graduation

## Run Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run hospitalist_calculator.py
```

## Deploy to Streamlit Cloud

1. **Push to GitHub:**
   ```bash
   git init
   git add .
   git commit -m "Initial commit: Hospitalist compensation calculator"
   git remote add origin https://github.com/YOUR_USERNAME/hospitalist-calculator.git
   git push -u origin main
   ```

2. **Deploy on Streamlit Cloud:**
   - Go to [share.streamlit.io](https://share.streamlit.io)
   - Click "New app"
   - Connect your GitHub repository
   - Set main file path: `hospitalist_calculator.py`
   - Click "Deploy"

3. **Share the URL** with faculty for self-service compensation estimates

## Files

- `hospitalist_calculator.py` - Main Streamlit application
- `requirements.txt` - Python dependencies
- `README.md` - This file

## Notes

- Estimates only - final numbers confirmed when schedule is published
- Based on FY27 compensation model parameters
- Does not include moonlighting or additional incentives

## Related

This calculator complements the annual schedule build process managed through Qgenda. See the parent folder for scheduling documentation.
