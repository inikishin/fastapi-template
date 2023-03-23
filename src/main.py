from fastapi import FastAPI

app = FastAPI()


@app.get('/')
def handle_root():
    return {
        'app': 'v1'
    }