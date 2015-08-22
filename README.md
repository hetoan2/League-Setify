# League Setify
A League of Legends item set builder. Generate item sets from specific games or certain user's build-style for a specified champion.

### Live Url
[http://leaguesetify.com/](http://leaguesetify.com/)

### About
Leage Setify is a web application created to help summoners quicky build item sets for use in the game [League of Legends](http://na.leagueoflegends.com/).

This project was created for the [Riot Games API Challenge 2.0](https://developer.riotgames.com/discussion/announcements/show/2lxEyIcE) by Tom Fuller (LoL NA Server: musouka, elswhere: hetoan2).

I do hope that this project can continue with input from the community to make it better in the future. So if you find any bugs, do not hesitate to create an issue on this GitHub page.

### Tech
This project was made possible by the following open source projects:
* [Python 2.7](https://www.python.org/) - A very great language for fast development.
* [Django 1.8](https://www.djangoproject.com/) - Web application framework for Python.
* [Sortable](https://github.com/RubaXa/Sortable) - Javascript library for drag-and-drop interfaces.
* [Twitter Bootstrap](http://getbootstrap.com/) - HTML, CSS, and JS framework for developing responsive websites.
* [Bootswatch](http://bootswatch.com) - Themes for Bootstrap.

And a very special thanks to [Riot Games](https://developer.riotgames.com/) for their APIs and documentation.

### How do I run this on my own server?
First, install Python 2.7 and Django 1.8, as these are required for this application to run.
It may be compatible with other versions, but this has not been tested.

Note: to run this code on your own server you must include your API key in the following files 
- \itemset_site\builder\models.py 
- \itemset_site\games\modes.py
- \itemset_site\search\modes.py

Just put your key in between the quotes on the line 
```api_key = ""```

Consider downloading [PyCharm](https://www.jetbrains.com/pycharm/) so that you can import the `\itemset_site\` directory as a project.
