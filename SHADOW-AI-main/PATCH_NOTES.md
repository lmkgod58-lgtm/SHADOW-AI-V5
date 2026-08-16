# Shadow AI 4.1.1 Patch Notes

- Message bubbles now calculate their own height from the label texture and keep the full message inside the rounded bubble.
- User and AI bubbles resize safely for Android screen/keyboard changes.
- The composer uses Android soft-input resize behavior so typed text remains visible above the keyboard.
- `/chat` and `/health` HTTPS requests explicitly use the certifi CA bundle and certificate verification.
- JSON request bodies are encoded explicitly as UTF-8 bytes, preventing the Android Latin-1 request-body failure seen with Unicode such as em dashes and curly quotes.
- Transient client/network errors get one automatic retry before the actual error is shown.
- Error messages no longer falsely claim Railway is offline when the failure happened inside the APK network client.
- Buildozer now packages requests, certifi, and openssl for the Android HTTPS stack.
- INTERNET and ACCESS_NETWORK_STATE remain explicitly declared.
