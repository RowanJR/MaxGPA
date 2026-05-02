### Program Description

MaxGPA is a program that allows a user to easily query a large set of grade data to determine which professors have the best historical grade distributions classes are searched by degree requirements; a degree requirement is selected, and the grade data of all professors who have taught each class required for that degree are displyed. 

### User Instructions

To use the MaxGPA program, you must first ensure docker is installed.

Navigate to the folder containing MaxGPA and run the command "docker compose up". Once the docker file has finished compiling, go to http://172.18.0.4:5000 (or http://127.0.0.1:5000/ if you encounter errors) on any web browser to access the locally hosted HTML. Here, you'll see options for the years you'd like to search, and the major you want to display information for. Entering these and pressing submit will display the data in easily readable graphs.

You can end the process by pressing ctrl+c in the terminal running docker, or running the "docker stop" command on the running containers. Unwanted docker images can be removed with "docker rmi" and "docker prune".

### Admin Instructions

Admin mode can be easily accessed in user mode by pressing the admin button in the top left corner of the page. This allows upload of the grade data you want to use, provided in csv format, and automatically adds it to the database upon upload. This must include a "TERM_DESC", "SUBJ", "NUMB", "INSTRUCTOR", and grade column fields (the same format as provided by the University of Oregon). Grade data csv files can also be manually added to the "Course_Grades" directory, located in the primary directory, but they will not be added to the database if added to the directory before startup; grade data added manually must be in the "Course_Grades" directory before the program is launched.

Degrees/degree requirements are located in degree_requirements.json, which can be directly edited to add new degrees, or CSV_to_JSON_requirements.py can be run on a csv of the degree requirements to obtain the json.