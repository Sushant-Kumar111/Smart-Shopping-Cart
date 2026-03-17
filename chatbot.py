import re
import sys

import mysql.connector


def _matches(text, keywords):
    """Return True if any keyword matches the start of a word in text."""
    for kw in keywords:
        if re.search(r"\b" + re.escape(kw), text):
            return True
    return False


class ShoppingMallChatbot:
    """A simple rule-based chatbot for The Great Indian Mall support."""

    # Mall configuration constants
    MALL_NAME = "The Great Indian Mall"
    MALL_ADDRESS = "Indira Nagar, Lucknow"
    MALL_PHONE = "011915221234567"
    MALL_EMAIL = "thegreatindianmall@gmail.com"
    MALL_HOURS = "10:00 AM to 10:00 PM, 7 days a week"

    GREETINGS = ["hello", "hi", "hey", "greetings", "howdy"]
    FAREWELLS = ["bye", "goodbye", "exit", "quit", "see you"]
    HELP_KEYWORDS = ["help", "menu", "option", "assist"]
    PRODUCT_KEYWORDS = ["product", "item", "stock", "inventory"]
    CUSTOMER_KEYWORDS = ["customer", "register", "membership"]
    BILL_KEYWORDS = ["bill", "invoice", "purchase", "checkout", "buy"]
    LOCATION_KEYWORDS = ["location", "address", "where", "place"]
    HOURS_KEYWORDS = ["hour", "time", "open", "close", "timing"]
    CONTACT_KEYWORDS = ["contact", "phone", "email", "reach"]

    def __init__(self):
        self.db = None
        self.cursor = None
        self.connected = False
        self._connect()

    def _connect(self):
        try:
            self.db = mysql.connector.connect(
                host="localhost", user="root", password=""
            )
            self.cursor = self.db.cursor()
            self.cursor.execute("use SHOPPING_MALL")
            self.connected = True
        except Exception as e:
            print(f"[Chatbot] Database connection unavailable: {e}", file=sys.stderr)
            self.connected = False

    def get_response(self, message):
        """Return a chatbot response for the given user message."""
        text = message.lower().strip()

        if not text:
            return "Please type a message so I can help you."

        if _matches(text, self.GREETINGS):
            return (
                f"Hello! Welcome to {self.MALL_NAME}. "
                "How can I assist you today? Type 'help' to see what I can do."
            )

        if _matches(text, self.FAREWELLS):
            return f"Thank you for chatting with us. See you soon! \U0001f600"

        if _matches(text, self.HELP_KEYWORDS):
            return self._help_text()

        if _matches(text, self.PRODUCT_KEYWORDS):
            return self._handle_product_query(text)

        if _matches(text, self.CUSTOMER_KEYWORDS):
            return (
                "For customer registration or management, use the "
                "Customer Menu (Option 2) from the main menu."
            )

        if _matches(text, self.BILL_KEYWORDS):
            return (
                "To create a bill or invoice, use the "
                "Bill Menu (Option 3) from the main menu."
            )

        if _matches(text, self.LOCATION_KEYWORDS):
            return f"{self.MALL_NAME} is located at {self.MALL_ADDRESS}."

        if _matches(text, self.HOURS_KEYWORDS):
            return f"{self.MALL_NAME} is open {self.MALL_HOURS}."

        if _matches(text, self.CONTACT_KEYWORDS):
            return (
                "Contact us:\n"
                f"  Phone: {self.MALL_PHONE}\n"
                f"  Email: {self.MALL_EMAIL}"
            )

        return (
            "Sorry, I didn't quite understand that. "
            "Type 'help' to see how I can assist you."
        )

    def _handle_product_query(self, text):
        if any(kw in text for kw in ["show", "list", "all", "available"]):
            return self._get_all_products()
        if _matches(text, ["price"]):
            return (
                "Please specify a product ID or name to check its price. "
                "For a full list, type 'show all products'."
            )
        if any(kw in text for kw in ["search", "find", "check"]):
            return "Please provide the product ID or name you want to search for."
        return self._get_all_products()

    def _get_all_products(self):
        if not self.connected:
            return (
                "Unable to connect to the database right now. "
                "Please check the connection and try again."
            )
        try:
            self.cursor.execute(
                "SELECT PRODUCT_ID, PRODUCT_NAME, QUANTITY, PRICE, DISCOUNT "
                "FROM PRODUCT_TABLE"
            )
            products = self.cursor.fetchall()
            if not products:
                return "No products are currently available in the inventory."
            header = f"\n{'ID':<12} {'Name':<20} {'Qty':<8} {'Price':<10} {'Discount'}\n"
            header += "-" * 58 + "\n"
            rows = "".join(
                f"{p[0]:<12} {p[1]:<20} {p[2]:<8} {p[3]:<10} {p[4]}%\n"
                for p in products
            )
            return "Available Products:" + header + rows
        except Exception as e:
            return f"Error fetching products: {e}"

    def _help_text(self):
        return (
            "Here is what I can help you with:\n"
            "  \u2022 Products  - Check available products and stock\n"
            f"  \u2022 Location  - Find the mall location ({self.MALL_ADDRESS})\n"
            f"  \u2022 Hours     - Mall opening and closing times ({self.MALL_HOURS})\n"
            "  \u2022 Contact   - Phone and email details\n"
            "  \u2022 Customer  - Info about customer registration\n"
            "  \u2022 Bill      - Info about billing and checkout\n\n"
            "For mall management (adding products, customers, bills), "
            "please use the Main Menu."
        )


def start_chat():
    """Start an interactive chat session with the shopping mall bot."""
    chatbot = ShoppingMallChatbot()
    print("=" * 60)
    print(f"\t\t{ShoppingMallChatbot.MALL_NAME} - Chat Support")
    print("=" * 60)
    print("Hi! I am your shopping assistant. Type 'bye' to exit chat.")
    print("=" * 60)

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nBot: Goodbye! Have a great day!")
            break

        if not user_input:
            continue

        response = chatbot.get_response(user_input)
        print(f"Bot: {response}")

        if _matches(user_input.lower(), ShoppingMallChatbot.FAREWELLS):
            break


if __name__ == "__main__":
    start_chat()
