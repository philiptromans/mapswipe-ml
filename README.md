# mapswipe-ml
A suite of tools for doing machine learning with the data from [Mapswipe](https://mapswipe.org/). Hopefully this project will grow into something that can be useful to the project.


## generate_dataset.py
`generate_dataset.py` is a tool for generating convenient machine learning datasets.
Example usage:
`./generate_dataset.py 6807 6794 6930 7064 7125 6918 7049 --bing-maps-key *Bing Maps API key* -o laos`

will create a directory called `laos`, with the following layout:
```
+ laos/
+--+ valid/
|  +-- built/
|  +-- bad_imagery/
|  +-- empty/
+--+ train/
|  +-- built/
|  +-- bad_imagery/
|  +-- empty/
+--+ test/
|  +-- solutions.csv
```

The directories will be full of satellite images downloaded from Bing Maps. This requires a Bing Maps API key, which you can register for [here](https://msdn.microsoft.com/en-us/library/ff428642.aspx). The images will be associated with the projects listed (i.e. `6807`, `6794`, ..., `7049`). You can include as many or as few projects as you like. Project IDs can be found at  http://mapswipe.geog.uni-heidelberg.de/

More documentation can be found by running `./generate_dataset.py --help`.

### How tiles are selected
`built` and `bad_imagery` tiles are selected if they have at least one vote from a user for that category, and no votes for another category. `empty` tiles are selected by randomly picking tiles from within the project boundary that have not been annotated by any user, i.e. they've always been swiped past and so there's no data available for them from the API. Tiles are selected until one class has no more candidate tiles, which means that all class sizes should be equal. Images that are explicitly missing (where Microsoft return a grey image with a crossed out camera on) are never included in any group.
