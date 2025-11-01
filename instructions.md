# Instructions to Run Tests Manually

Here are the steps to run the automated tests for the GeoWatch backend application.

## 1. Open Your Terminal

Open a terminal or command prompt on your system.

## 2. Navigate to the Project Directory

Navigate to the root directory of the GeoWatch project:

```bash
cd C:\Users\hariy\OneDrive\Documents\PROJECTS\geoWatch
```

## 3. Activate the Virtual Environment

Activate the Python virtual environment. This is crucial to ensure you are using the correct dependencies.

```bash
.\venv\Scripts\activate
```

Your terminal prompt should now be prefixed with `(venv)`.

## 4. Navigate to the Backend Directory

Change into the `backend` directory where the application and tests reside:

```bash
cd backend
```

## 5. Run the Tests

Now, run `pytest`. It will automatically discover and run the tests in the `tests` directory.

```bash
pytest
```

You should see output from `pytest` indicating the test results. The tests will make live calls to your Firestore database, so make sure your environment variables are set up correctly in the `.env` file as described previously.
