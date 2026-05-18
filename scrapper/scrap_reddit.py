import praw

reddit = praw.Reddit(
    client_id="VOTRE_CLIENT_ID",
    client_secret="VOTRE_CLIENT_SECRET",
    user_agent="script:mon_rag_lol:v1.0"
)

subreddit = reddit.subreddit("summonerschool")

for submission in subreddit.search("wave management", limit=10):
    print(submission.title)
    print(submission.selftext)