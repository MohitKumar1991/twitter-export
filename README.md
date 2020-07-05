# twitter-export
[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy)

### Search through your followers and send them mass DMs. Uses Twitter APIs (which severly rate limit this)

#### Features
- Export all your followers (works on million+ followers - takes a couple of hours)
- Filter followers using multiple parameters
- Send DMs to a selected group of followers
- Create subscription links where people can submit emails
- Manage that email list as well as create affiliate links to reward people who help you get more emails

#### HEROKU INSTRUCTIONS (After clicking on the Deploy to Heroku Button)
- Set the password and username using `HTTP_USERNAME` and `HTTP_PASSWORD`. Default are `noob` and `nommr` respectively.
- Go to App Overview in the (Heroku Dashboard)[https://dashboard.heroku.com]
- Turn on the Worker in the heroku section
![Heroku App Overview](https://raw.githubusercontent.com/MohitKumar1991/twitter-export/f/salchemy/docs/heroku_app_overview.png)
![Heroku Dyno Configure](https://github.com/MohitKumar1991/twitter-export/blob/f/salchemy/docs/worker_dyno_off.png?raw=true)
![Heroku Worker On](https://github.com/MohitKumar1991/twitter-export/blob/f/salchemy/docs/worker_start.png?raw=true)


#### LOCAL INSTALLATION
- Copy the entire repo
- Install Poetry - https://python-poetry.org/docs/
- Go to the repo directory ..../twitter-export/
- Run the following commands

```shell
poetry install
make start_worker
make start_server
```

To stop worker locally
```
make stop_worker
```

This will 
1. Start a background process which will download all your followers locally
2. Run a web app which will serve a UI to explore them as well as filter them.
3. You can then create Mass DM campaigns

A few things:-
1. The query section in the search page takes a SQlite3 Query and performs it over all the followers
2. The Message in the campaign is parsed as a Jinja2 template with follower details injected in follower variable. So to write the name of the follower put {{follower.name}}

DISCLAIMER - WIP - Plz post feature requests etc

Related to https://github.com/balajis/twitter-export

