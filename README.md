# Minh Thy Chatbot - Your Customizable AI Companion

Minh Thy is an interactive, highly customizable AI chatbot designed to provide a uniquely human-like conversational experience. Built with Flask and Socket.IO, Minh Thy adapts her personality and communication style based on your preferences, making every chat session engaging and personalized.

## Features

-   **Real-time Chat:** Engage in dynamic, real-time conversations.
-   **Customizable Personality:** Adjust Minh Thy's "mood" (0-100) to influence her responses, tone, and overall persona.
-   **Human-like Interactions:**
    -   Proactive messaging when you're inactive (within set hours).
    -   Simulated online/offline status and varied response delays.
    -   Human-like typing speed, pauses, and even occasional typos with corrections.
    -   Ability to use text formatting (bold, italics, strikethrough) and emojis for emphasis.
    -   Context-aware responses, remembering recent conversation points.
-   **Multi-part Messaging:** Minh Thy can send multiple short messages in sequence, mimicking natural human chat.
-   **Persistent Conversations:** All chat history, settings, and memories are saved locally in `chat_data.db`.

## Installation

### Prerequisites

-   Python 3.8+
-   `pip` (Python package installer)

### Steps

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/your-repo-name.git
    # Navigate to the Minh Thy project directory
    cd your-repo-name/duongdev/minhthy 
    ```
    *(If you copied the folder to a standalone location, navigate there instead.)*
2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: .\venv\Scripts\activate
    ```
3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Configuration

1.  **API Key:**
    Minh Thy uses the Bytez SDK to connect to Google's Gemini models. You need to provide your Bytez API key.
    Open `app.py` in the `minhthy` directory and replace the placeholder API key with your actual Bytez API key:
    ```python
    sdk = Bytez("YOUR_BYTEZ_API_KEY_HERE") # Replace "YOUR_BYTEZ_API_KEY_HERE"
    ```

2.  **In-App Settings:**
    You can customize Minh Thy's name, your name, and her "mood" (0-100) directly from the chatbot's web interface. These settings are saved per conversation.

## Usage

1.  **Start the server:**
    ```bash
    python app.py
    ```
    For background execution (recommended for production):
    ```bash
    nohup python app.py &
    ```
2.  **Access the Chatbot:**
    Open your web browser and navigate to `http://localhost:5000` (default port when running standalone).

## Contributing

Contributions are welcome! If you have suggestions or improvements, please feel free to open an issue or submit a pull request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
