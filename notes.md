- LLM_cache has a version with the code so things get invalidated easily
- Testing sets up one db with session rollback for isolation, so you can do fast tests
- The Code and meidcation management agent will need more details on most commonly used codes and more context
- The code might need inferring from other details to udnertand whether its without complications or with etc.
- the medication has lots of forms and we'll need to normalize into what is most frequent most likely.

- The coding and RxNorm should get enough context to be able to get the right answer. The API calls should get top N and then the LLM can decide the best option based on context.
  - Adding memory, a DB of "best" or most common corpuses will help with the quality

- atorvastatin 20mg vs 20mg tab gives different results of specific vs nonspecific. Will need to resolve these with some sort of term exppansion, prior understanding or linked term preference. 
-- There is an example store that can be used to create preferences and priorities to seed the system. Its not persistent yet.

- Plan for security of secrets
