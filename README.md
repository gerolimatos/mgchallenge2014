mgchallenge2014
===============

SF Movie Database Code Challenge
Mark Gerolimatos
mark@gerolimatos.com
650 703-4774
“Mark Gerolimatos” on LinkedIn 
Facebook.com/mark.gerolimatos
Gerolimatos.com (currently on load to the PN Gerolymatos coporation…yes, 3rd cousins)

App link: http://mgchallenge2014.appspot.com
git Hub (uhh, you're here already): https://github.com/gerolimatos/mgchallenge2014


__Purpose:__
It’s a fact: people come from all over the world to trace the footsteps of their favorite actors and actresses from their favorite movies. The throng got so bad that the owners of Jimmy Stewart’s apartment from Vertigo had to build a wall surrounding the building, thus masking its location.

This app seeks to make their lives harder.

What this app does:
The City of San Francisco has put together a Socrates website cataloguing most (if not all) movies made in San Francisco (but apparently not TV shows…I just used my own app to look up Streets of San Francisco…of COURSE I cover the ‘The’ case…and it wasn’t there). The database consists of movie names, actors, producers, release year, and of course, the filming locations.

However, it’s a pretty boring site (assuming you are not excited by spreadsheets): extremely governmental in its focus. They do however provide an SQL-like RESTful interface called “SoQL” (and apparently SODA, apparently because acronyms are free). This API provides the raw JSON data behind the dry interface.
With this data, I have put together a medium-sized app and interface to allow users to view this data graphically on a Google™Map. Users can enter in text, which will then be autocompleted. They can then choose from the results (no freelancing allowed) and be taken to a map with markers:
*	If a location search, the (single) marker will have an info window popup with the titles filmed at that site. The links in that popup are live, and when clicked, perform the appropriate title search.
*	If a title search, each of the entries in the database will have a marker dropped on the SF map. These markers are “live”, and when clicked (they will turn green), do the appropriate location search.
Note that due to time constraints, actor searches were removed (as it is just “more of the same” as the other two searches). And since the IMDB interface is not highly supported, links to IMDB were left out in this phase of the application (although I would love to add it in).

__What this app is:__
The backend of this application was written completely in Python. The choice was relatively obvious: PERL is no longer the language of choice for such things (although it is finding an afterlife in spirit via Scala’s amazingly PERL-like programming model); PHP’s syntax and strange equality rules make it less suitable. Python, with its nearly non-existent syntax, support  from Google and rather large set of available libraries then fell out naturally. 
The packages used were:
*	The Google GeoCoding API (the GoogleMaps API itself was *not* use…more below)
*	Kenneth Reitz’s “Requests” HTTP client library
*	The JQuery.Autocomplete JavaScripts
*	The GoogleMaps client/Javascript API
*	A little code taken here and there from Stack Overflow
These packages were chosen both for their ease of use and installation as well as functional abilities. Although future users of the JQuery.Autocomplete package should know that the example given is actually incorrect: many hours were wasted on that. You should use the readme from the package’s GiTHub project instead.
(Note: all addresses of these packages are in the code)

Speaking of Python Syntax:
Being a multiglot programmer who has written in everything from assembler, LISP, Fortran IV all the way to Scala, I make some slight changes to the Python syntax: namely, 
*	(parenthesize) the clauses in an if : and elif : statement
*	liberally use pseudo-brackets (#{, #}) to allow for ease of block search (especially when using VI
*	create “Parent” pointers in each derived class so that I don’t have to keep using the simply horrendous super(MyClass, self) syntax

Design Imperative: RESTiness over Database Storage
At all times, state was to be avoided (short of caching). Being a coding challenge, this was written in off hours, and given that the development time was further reduced by unforeseen events, state management simply took a back seat to clean and efficient implementation. 
The biggest example of this is use of the Google Maps webclient API as opposed to the “server” API. In the “server” API, the application scripts on the server would need to generate a map on a remote API, and those map IDs then sent to the client. The problem with the latter method is that there would then be a triad of state between the server, the client and The Google™. Experience has shown that complexity really does rise combinatorically with each party that is added to shared state.

By instead using JavaScript code chunks to specify map boundaries and markers, it was possible to make this completely persistent state free…the only state needed being caching to improve performance. But as with any cache scheme, the app would work just fine without it, albeit somewhat slower.

__Modules:__
The application thus exists of the following handful of modules:
Web/HTTP GET service module, which creates the web pages source to send to the client (as I am using Google™Application Engine, there is almost no work in managing HTTP state)
SoQL module charged with acting as an interface to the SFMovies Database website
Google Geocoding web interface, and code to generate the browser-side Javascript code
Autocomplete module, consisting onf ternary tree code  modified to be more readable, more correct (there were a couple of bugs in it), and more functionally friendly; the aforementioned JQuery.Autocomplete Javascript code
Caches: simple unbounded cache, LRU cache and an Expiring Cache
Auotest module that runs on initialization. While it does not prevent the app from loading, it will log any errors. I relied on this module to determine my Google Map Service account state (eventually running out of courtesy geolocation requests).

Dataflow:
The dataflow of a request is as follows:
*HTTP URL query data is collected to determine the type of request: Autocomplete Query, Location Search, Title Search, “Welcome Page” (i.e. SF City map with no markers) or control requests
*If autocomplete, the query data is fed to the ternary tree code (one tree for movies, one tree for addresses), from which JQuery.Autocomplete-compliant JSON is created
*If title search, an SoQL query is issued (select locations where title = titlename), and each of the locations is passed to the Gooogle™ geolocator. The resultant geographic specifiers are then encoded as GoogleMaps markers and sent to the browser as Javascript
*If a location search, an SoQL is issued (select titles where locations = loc). The results are used to create links to associated title searches. The single location is then geolocated, and a single-marker map is created.

Optimizations: CACHING!
As mentioned previously, the time constraints, as well as the management headaches of a persistent state system made stored maps unfeasible. In order to win back performance time lost to the web browser (although, it should be pointed out that it has not been proven to myself that such a scheme is actually any faster on the browser side), caching was very heavily relied upon. Since the movie data itself is only about 100k total, there was absolutely no reason to not cache until the cows came home. Note that I purposely didn’t just “download the entire database”, as I considered that cheating (i.e. not a real solution). Obviously, this was necessary for the autocomplete database, but all others were cached on demand.
The main cache points were:
*	URL/result caching: the entire result of a given URL would be saved in a 100-entry LRU cache. Note that any error in the results (such as missing partial data) would cause that URL to not be cached. This cache is highly effective, often returning an entire page in less than a second.
*	Remote HTTP lookup caching. Because of the possibility of multiple requests sharing the same backend data, and since I didn’t “cheat” and just load the entire dataset in, requests to the SFMovie database were cached. Additionally, since the Google Geolocator API is not free, the results to that API are similarly cached, not only to speed performance, but also to save me money. That’s a good thing.
*	Autocomplete caching. The 100-entry LRU cache for URLs is a threadsafe implementation requiring synchronizers to maintain consistency. I considered this to be too slow for autocompletion, and thus used a fast hashtable cache  (addition only, no cleaning) to store the autocomplete results.
*	Caching of URL encoding and decoding. Since either the URL encoded or decoded versions of strings were needed in various places, I had initially been caching those. However, since the vast number of strings were very very short, I determined that the “amortized cost” of rehash to not be worth the risk. This cache was turned off.

A word about atomicity:
Great reliance was paid to the atomic nature of Python scalar assignment. That is, it is impossible to pollute memory by a race condition of scalar assignment. By being careful to have a single point of access to data structures, and by making a personal ref to a data structure, combined with being careful to not delete or otherwise destructively modify existing data stores, it was possible to create a threadsafe application with no (syntactic) synchronizers. Of course, there are most certainly synchronizers inside the Python engine.
The only place explicit synchronization became necessary was in the LRU and Expiring caches, as they by definition do destructive changes to the data state. Note that these two caches were actually somewhat gratuitous: the dataset is not big enough to worry about self-reducing caches. However, these would normally be used in such situations, and so were included.

__Things Not Done:__
Due to time constraints, the following things had to be dropped:
*	The oft-mentioned server-side map generation. Not for development costs as much as support complexity (namely maintaining persistent state). This would also require associated databases.
*	A “cache cleaner”. While the code is designed at all points to be threadsafe, the simple fact is that the SF Movie database does not change contents all that often. For instance, it has not changed during my development. This made cache invalidation code, no matter how simple (given my design for it) a risky issue: there would be no way to adequately test it in time.
*	Better UI. Simply put, using a better UI toolkit(s) would make for a better UI. However, the point of this application was to show engineering and design principles and not UI design (as I am not applying for a UI design position). Enough was done to meet the functional requirements, along with a few add-ons (such as being able to click on a marker to). Given enough time, empty-calorie snack foods and coffee, a better UI could of course be designed.
*	System preload module. There appears no way to convince the Google App Engine to initialize the Python state earlier than first GET request. I am sure that further research will turn something up, but until then, I have made a simple start api (mgchallenge2014.appspot.com/?cmd=start)  that will cause the Python machine to load. Note that there appear to be more than one instance created by the App Engine, it may be necessary to run the start command two or three times to preload them all.
* Routes to the locations. A nice feature to have, but time ran out.
* IMDB links. As mentioned previously, IMDB's API is not particularly open, and thus the time spent figuring out and spelunking it was not worth the loss of sleep. I would have LOVED to include pictures from the locations on each location (using the Google Map image API).
* A template-based HTML generator. A production-quality generator (where one provides html code templates, and it does all
the formatting) would be ideal. This is not something I would anticipate writing, as there are most certainly plenty of
templates out there.


