# twitter-export

### Search through your followers and send them mass DMs. Uses Twitter APIs (which severly rate limit this)

#How to install
- Copy the entire repo
- Install Poetry - https://python-poetry.org/docs/
- Go to the repo directory ..../twitter-export/
- Run the following commands

```shell
poetry install
poetry run server
```

This will 
1. Start a background process which will download all your followers locally
2. Run a web app which will serve a UI to explore them as well as filter them.
3. You can then create Mass DM campaigns


A few things:-
1. The query section in the search page takes a SQlite3 Query and performs it over all the followers
2. The Message in the campaign is parsed as a Jinja2 template with follower details injected in follower variable. So to write the name of the follower put {{follower.name}}

DISCLAIMER - This was done after a weekend hackathon as I already work at a full time job. By end June I plan on smoothing out most bugs as well as making everything much easier to use etc. Then I will start adding more features.

Related to https://github.com/balajis/twitter-export

