# Image Template Editor (Demo)

## Run in VS Code
1. Install Python 3.10 or newer.
2. Open this folder in VS Code.
3. Open Terminal and run:

   ```bash
   python -m venv .venv
   ```

   Windows:
   ```bash
   .venv\Scripts\activate
   ```

   macOS/Linux:
   ```bash
   source .venv/bin/activate
   ```

4. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

5. Start the app:

   ```bash
   streamlit run app.py
   ```

The app opens in your browser, usually at http://localhost:8501.

## Free hosting
Push `app.py`, `template.png`, and `requirements.txt` to a GitHub repository, then create an app on Streamlit Community Cloud and select `app.py`.

## Notes
- `template.png` is the supplied reference image used for demo purposes.
- This safe demo app does not replace the original ticket's identifying fields. It shows the entered values in a separate panel and adds a prominent `SAMPLE • NOT VALID` watermark to the output.
- For a different authorized promotional template, adjust the layout in `app.py`.
