from flask import Flask, request, jsonify
import requests
import spacy

app = Flask(__name__)
nlp = spacy.load("en_core_web_sm")


class MonsterrrAboutProducts:
    def __init__(self):
        self.product = None

    def create_tech_product(self, name, features, price):
        self.product = TechProduct(name, features, price)

    def introduce_innovation(self, new_features):
        if self.product:
            self.product.introduce_innovation(new_features)
        else:
            return {"message": "No product created yet."}, 400

    def meet_customer_demand(self, customer_feedback):
        if self.product:
            new_features = self.analyze_feedback(customer_feedback)
            self.product.introduce_innovation(new_features)
            return {"message": "Customer demand met successfully."}, 200
        else:
            return {"message": "No product created yet."}, 400

    def display_product_information(self):
        if self.product:
            return {
                "product_name": self.product.name,
                "product_features": self.product.features,
                "product_price": self.product.price
            }
        else:
            return {"message": "No product created yet."}, 400

    def analyze_feedback(self, customer_feedback):
        new_features = []
        for feedback in customer_feedback:
            doc = nlp(feedback)

            for token in doc:
                if token.pos_ == "NOUN" or token.pos_ == "ADJ":
                    new_features.append(token.lemma_)

        return list(set(new_features))

    def get_sentiment(self, text):
        # Call the sentiment analysis API
        response = requests.post("https://api.example.com/sentiment", json={"text": text})

        if response.status_code == 200:
            sentiment = response.json().get("sentiment")
            return sentiment
        else:
            print("Failed to get sentiment.")
            return None

    def get_named_entities(self, doc):
        entities = []
        for ent in doc.ents:
            entities.append((ent.text, ent.label_))
        return entities

    def fetch_products(self):
        # Call the products API
        response = requests.get("https://api.example.com/products")

        if response.status_code == 200:
            products = response.json()
            return products
        else:
            print("Failed to fetch products.")
            return None


class TechProduct:
    def __init__(self, name, features, price):
        self.name = name
        self.features = features
        self.price = price

    def introduce_innovation(self, new_features):
        self.features.extend(new_features)


assistant = MonsterrrAboutProducts()


@app.route("/create_product", methods=["POST"])
def create_product():
    data = request.get_json()
    name = data.get("name")
    features = data.get("features")
    price = data.get("price")

    if not all([name, features, price]):
        return {"message": "Incomplete product data."}, 400

    assistant.create_tech_product(name, features, price)
    return {"message": "Tech product created successfully."}, 200


@app.route("/introduce_innovation", methods=["POST"])
def introduce_innovation():
    data = request.get_json()
    new_features = data.get("new_features")

    if not new_features:
        return {"message": "No new features provided."}, 400

    response, status_code = assistant.introduce_innovation(new_features)
    return response, status_code


@app.route("/meet_customer_demand", methods=["POST"])
def meet_customer_demand():
    data = request.get_json()
    customer_feedback = data.get("customer_feedback")

    if not customer_feedback:
        return {"message": "No customer feedback provided."}, 400

    response, status_code = assistant.meet_customer_demand(customer_feedback)
    return response, status_code


@app.route("/product_information", methods=["GET"])
def product_information():
    response = assistant.display_product_information()
    return response, 200


if __name__ == "__main__":
    app.run()
