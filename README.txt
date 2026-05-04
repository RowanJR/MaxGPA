================================================================================
 MaxGPA
================================================================================

 CREATED April 2026

 AUTHORS
  Rowan Moore, Hayden Oelke, Caeleb Renner, Jake Seiberg


DESCRIPTION
  MaxGPA is a locally hosted web application that allows students to explore historical grade distribution data for courses required by their degree program. Users select a major and an academic year range; the system displays per-course, per-instructor grade distributions as interactive bar charts. An Admin panel allows authorized users to upload new grade data in CSV format without restarting the application.


PURPOSE
  Created for CS 422, Software Methodologies, Project 1 by group 8.
 

DEPENDENCIES
  Required:
    - Docker Desktop (https://www.docker.com/products/docker-desktop)
        Includes Docker Engine and Docker Compose.
        No other software needs to be installed manually.
 
  Installed automatically by Docker on compile:
    - Python 3.12
    - Flask >= 3.0.0
    - PyMongo >= 4.6.0
    - pandas >= 2.0.0
    - MongoDB 6 (runs as a separate Docker service)
 
  Optional (admin utilities only, run outside Docker):
    - Python 3.12
 
SETUP AND RUNNING THE PROGRAM
  1. Ensure Docker Desktop is installed and running on your machine.
     Verify with: docker --version
     *to install docker, visit https://www.docker.com/get-started/
 
  2. Place any grade data CSV files in the Course_Grades/ directory before
     starting the application. These Files are automatically read on startup.
 
  3. Open a terminal, navigate to this directory, and run:
        docker compose up
 
  4. Wait for Docker to finish building and starting all services. When ready,
     open any web browser and go to:
        http://127.0.0.1:5001
 
  5. Select a major and academic year range (if these say "loading..." there is no grade data added yet. Press the admin button in the top left to add grade data), then click "Generate Report". 
 
  To stop the application, press Ctrl+C in the terminal running Docker, or run:
        docker compose down
 
 
ADDITIONAL SETUP
  Adding grade data after startup:
    New CSV files can be uploaded at any time using the Admin panel. Click the "Admin" button in the top-left corner of the application, then drag and drop or browse for a CSV file and click "Upload CSV". Files must match the University of Oregon grade data format (columns: SUBJ, NUMB, INSTRUCTOR, TERM_DESC, and grade columns).
 
  Adding or updating degree requirements:
    Degree requirements are stored in degree_requirements.json and can be edited directly. Alternatively, run update_requirements.py on a formatted Excel spreadsheet (you can edit the one provided in this program directory) to regenerate this file automatically:

        python update_requirements.py --input Degree_Requirements.xlsx
 
  Port conflict:
    The application uses port 5001. If another program is using this port, see the Installation Instructions document for steps to free it before running docker compose up.
 
 
DIRECTORY STRUCTURE
  /Course_Grades/
      Contains the CSV grade data files loaded into MongoDB at startup. Add new CSV files here before running docker compose up to have them imported automatically.
 
  /static/
      Static frontend assets (CSS stylesheets, JavaScript) served by Flask.
 
  /templates/
      HTML template files rendered by Flask. Contains index.html, the main
      single-page frontend.
 
  Root-level files of note:
    app.py                      Flask backend; serves the UI and all API endpoints
    import_csv.py               Startup script; imports CSVs into MongoDB
    update_requirements.py      Admin utility; converts Excel to degree_requirements.json
    CSV_to_JSON_requirements.py Utility; exports or re-routes degree_requirements.json
    degree_requirements.json    Defines the degrees and required courses
    requirements.txt            Python package dependencies
    Dockerfile                  Container image definition
    docker-compose.yml          Defines and links the web, database, and importer services
