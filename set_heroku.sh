#!/bin/zsh

while IFS= read -r line
do
  echo "Setting $line..."
  heroku config:set $line
done < ".env"
heroku config:set GOOGLE_PRIVATE_KEY="$(cat ./.google_secret_key)"