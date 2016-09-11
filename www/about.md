# About xd.saul.pw

xd.saul.pw is a system I put together to practice my data pipeline and preservation skills.
It collects daily crosswords from several sources and converts them into .xd, a plain-text format designed for maximum data flexibility.
It then compares them against the rest of the crosswords in the corpus, and generates this static website.

I call this a 'cloud capsule'. It's a long-form web service that curates a longitudinal dataset for future crossword scholars.

I tried to design this crossword cloud capsule to be self-sustaining, which for me means a robust and low-maintenance system that can run in perpetuity at very little cost.
To this end, I chose a kind of ‘long serverless’ architecture, which does daily batch processing, rather than a continuous server or a newfangled collection of asynchronous cloud services.

I'd like this system to survive until all of the crossword data can be released publicly, but it will likely fall short of this goal.  I took great care with the data formats and organization, so that the curated data could be easily salvaged by a capable and responsible steward. [Download the public dataset](/data#download).

Please send all suggestions, offers, and complaints to [xd@saul.pw](mailto:xd@saul.pw).

[Saul Pwanson](saul.pw)

### Many Thanks To

* Barry Haldiman, for collecting so diligently;
* David Steinberg and the [Pre-Shortzian Puzzle Project (PSPP)](www.preshortzianpuzzleproject.com), for inspiring me;
* Jim Horne, Jeff Chen, and [xwordinfo.com](xwordinfo.com) for frustrating me so nicely;
* Kevin McCann and [cruciverb.com](cruciverb.com), for useful discussions on crossword creation;
* [Timothy Parker](https://en.wikipedia.org/wiki/Timothy_Parker_(puzzle_designer)) and [Ollie Roeder](http://fivethirtyeight.com/features/a-plagiarism-scandal-is-unfolding-in-the-crossword-world/), for providing some [drama in the form of #gridgate](https://twitter.com/hashtag/gridgate);
* Joseph Gratz at [Durie Tangri LLP](durietangri.com), for his generous legal counsel;
* my friends and family, for supporting me in my crazy projects;
* and all the constructors, editors, and publishers, for producing such great puzzles in the first place!

