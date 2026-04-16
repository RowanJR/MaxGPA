the current structure runs a docker container for the flask server and the mongo database. 

To compile and run, execute "docker compose up" in the base directory. Stop it with ctrl+c, and make sure to remove old stopped containers with "docker containers prune"/"docker rm -f $(docker ps -aq)", then remove old images with "docker rmi -f $(docker images -aq)".

once running, access localhost with http://127.0.0.1:5000/ in your browser.