from quart import Quart, render_template

app = Quart(__name__, template_folder='templates')

@app.route("/")
async def index():
    # Provide dummy username to render the dashboard view
    return await render_template("index.html", username="TestAdmin")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
