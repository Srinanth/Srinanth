import os
import sys
import json
import urllib.request
from datetime import datetime, timedelta

# Configuration
USERNAME = "Srinanth"
OUTPUT_SVG = "assets/stats.svg"

# Mock data for local testing or if token is missing
MOCK_DATA = {
    "name": "Srinanth MV",
    "stars": 125,
    "commits": 363,
    "prs": 24,
    "issues": 3,
    "total_contributions": 1157,
    "current_streak": 9,
    "longest_streak": 24
}

def fetch_github_stats():
    token = os.environ.get("STATS_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        print("No GitHub Token found. Using mock data for rendering.")
        return MOCK_DATA

    # We will fetch data from GitHub GraphQL API
    url = "https://api.github.com/graphql"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # Get last 365 days of contributions
    today = datetime.utcnow()
    one_year_ago = today - timedelta(days=365)
    
    query = """
    query($login: String!, $from: DateTime!, $to: DateTime!) {
      user(login: $login) {
        name
        pullRequests {
          totalCount
        }
        issues {
          totalCount
        }
        repositories(first: 100, ownerAffiliations: OWNER, privacy: PUBLIC) {
          nodes {
            stargazerCount
          }
        }
        contributionsCollection(from: $from, to: $to) {
          totalCommitContributions
          restrictedContributionsCount
          contributionCalendar {
            totalContributions
            weeks {
              contributionDays {
                contributionCount
                date
              }
            }
          }
        }
      }
    }
    """
    
    variables = {
        "login": USERNAME,
        "from": one_year_ago.isoformat() + "Z",
        "to": today.isoformat() + "Z"
      }
    
    req_data = json.dumps({"query": query, "variables": variables}).encode("utf-8")
    req = urllib.request.Request(url, data=req_data, headers=headers)
    
    try:
        with urllib.request.urlopen(req) as response:
            res = json.loads(response.read().decode("utf-8"))
            
            if "errors" in res:
                print("GraphQL Errors:", res["errors"])
                return MOCK_DATA
                
            user_data = res["data"]["user"]
            
            # Calculate total stars
            stars = sum(repo["stargazerCount"] for repo in user_data["repositories"]["nodes"])
            
            # Lifetime PRs and Issues
            prs = user_data["pullRequests"]["totalCount"]
            issues = user_data["issues"]["totalCount"]
            
            # Contribution calendar and streaks
            calendar = user_data["contributionsCollection"]["contributionCalendar"]
            total_contributions = calendar["totalContributions"]
            
            # Extract daily contribution counts
            days = []
            for week in calendar["weeks"]:
                for day in week["contributionDays"]:
                    days.append({
                        "date": datetime.strptime(day["date"], "%Y-%m-%d").date(),
                        "count": day["contributionCount"]
                    })
            
            days.sort(key=lambda x: x["date"])
            
            # Calculate current and longest streak
            current_streak = 0
            longest_streak = 0
            temp_streak = 0
            
            today_date = datetime.utcnow().date()
            yesterday_date = today_date - timedelta(days=1)
            
            for d in days:
                if d["count"] > 0:
                    temp_streak += 1
                    if temp_streak > longest_streak:
                        longest_streak = temp_streak
                else:
                    temp_streak = 0
            
            current_streak = 0
            streak_date = today_date
            
            today_contrib = next((d["count"] for d in days if d["date"] == today_date), 0)
            yesterday_contrib = next((d["count"] for d in days if d["date"] == yesterday_date), 0)
            
            if today_contrib > 0:
                streak_date = today_date
            elif yesterday_contrib > 0:
                streak_date = yesterday_date
            else:
                streak_date = None
                
            if streak_date:
                consecutive_active = 0
                check_date = streak_date
                while True:
                    contrib = next((d["count"] for d in days if d["date"] == check_date), 0)
                    if contrib > 0:
                        consecutive_active += 1
                        check_date -= timedelta(days=1)
                    else:
                        break
                current_streak = consecutive_active
            
            commits = user_data["contributionsCollection"]["totalCommitContributions"]
            
            return {
                "name": user_data["name"] or USERNAME,
                "stars": stars,
                "commits": commits,
                "prs": prs,
                "issues": issues,
                "total_contributions": total_contributions,
                "current_streak": current_streak,
                "longest_streak": max(longest_streak, current_streak)
            }
            
    except Exception as e:
        print(f"Error fetching data from GitHub API: {e}. Using mock data.")
        return MOCK_DATA

def generate_svg(data):
    os.makedirs(os.path.dirname(OUTPUT_SVG) or ".", exist_ok=True)
    
    width = 600
    height = 200
    
    svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" fill="none">
  <style>
    .card {{
      fill: #0d1117;
      stroke: #30363d;
      stroke-width: 1.5;
      rx: 12px;
    }}
    .title {{
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      font-weight: 700;
      font-size: 16px;
      fill: #58a6ff;
    }}
    .stat-label {{
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      font-weight: 500;
      font-size: 13px;
      fill: #8b949e;
    }}
    .stat-value {{
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      font-weight: 700;
      font-size: 14px;
      fill: #f0f6fc;
    }}
    .icon {{
      fill: #8b949e;
    }}
    .divider {{
      stroke: #21262d;
      stroke-width: 1;
    }}
    .stat-row:hover .icon {{
      fill: #58a6ff;
      transition: fill 0.2s ease;
    }}
    .stat-row:hover .stat-label {{
      fill: #c9d1d9;
      transition: fill 0.2s ease;
    }}
    .streak-row:hover .icon {{
      fill: #ff7b72;
      transition: fill 0.2s ease;
    }}
    .streak-row:hover .stat-label {{
      fill: #c9d1d9;
      transition: fill 0.2s ease;
    }}
  </style>

  <rect width="{width}" height="{height}" class="card" />

  <g transform="translate(25, 25)">
    <text x="0" y="15" class="title">GitHub Stats</text>
    
    <g class="stat-row" transform="translate(0, 35)">
      <path class="icon" d="M8 .25a.75.75 0 0 1 .673.418l1.882 3.815 4.21.612a.75.75 0 0 1 .416 1.279l-3.046 2.97.719 4.192a.75.75 0 0 1-1.088.791L8 12.347l-3.766 1.98a.75.75 0 0 1-1.088-.79l.72-4.194L.818 6.374a.75.75 0 0 1 .416-1.28l4.21-.611L7.327.668A.75.75 0 0 1 8 .25Z" transform="scale(1.1)"/>
      <text x="25" y="12" class="stat-label">Total Stars Earned</text>
      <text x="180" y="12" class="stat-value">{data['stars']}</text>
    </g>

    <g class="stat-row" transform="translate(0, 67)">
      <path class="icon" d="M10.5 7.75a2.5 2.5 0 1 1-5 0 2.5 2.5 0 0 1 5 0Zm1.43.75a4.002 4.002 0 0 1-7.86 0H.75a.75.75 0 1 1 0-1.5h3.32a4.002 4.002 0 0 1 7.86 0h3.32a.75.75 0 1 1 0 1.5h-3.32Z" transform="scale(1.1)"/>
      <text x="25" y="12" class="stat-label">Commits (Last Year)</text>
      <text x="180" y="12" class="stat-value">{data['commits']}</text>
    </g>

    <g class="stat-row" transform="translate(0, 99)">
      <path class="icon" d="M7.177 3.073L9.573.677A.25.25 0 0110 .854v4.792a.25.25 0 01-.427.177L7.177 3.427a.25.25 0 010-.354zM3.75 2.5a.75.75 0 100 1.5.75.75 0 000-1.5zm-2.25.75a2.25 2.25 0 113 2.122v5.256a2.251 2.251 0 11-1.5 0V5.372A2.25 2.25 0 011.5 3.25zM11 12.5a1.5 1.5 0 100-3 1.5 1.5 0 000 3z" transform="scale(1.1)"/>
      <text x="25" y="12" class="stat-label">Pull Requests</text>
      <text x="180" y="12" class="stat-value">{data['prs']}</text>
    </g>

    <g class="stat-row" transform="translate(0, 131)">
      <path class="icon" d="M8 9.5a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3z M8 0a8 8 0 1 0 0 16A8 8 0 0 0 8 0zm0 14.5a6.5 6.5 0 1 1 0-13 6.5 6.5 0 0 1 0 13z" transform="scale(1.1)"/>
      <text x="25" y="12" class="stat-label">Total Issues</text>
      <text x="180" y="12" class="stat-value">{data['issues']}</text>
    </g>
  </g>

  <line x1="300" y1="20" x2="300" y2="180" class="divider" />

  <g transform="translate(325, 25)">
    <text x="0" y="15" class="title" fill="#ff7b72">Contributions &amp; Streaks</text>

    <g class="streak-row" transform="translate(0, 35)">
      <path class="icon" d="M4.75 0a.75.75 0 0 1 .75.75V2h5V.75a.75.75 0 0 1 1.5 0V2h1.25c.966 0 1.75.784 1.75 1.75v10.5A1.75 1.75 0 0 1 13.25 16H2.75A1.75 1.75 0 0 1 1 14.25V3.75C1 2.784 1.784 2 2.75 2H4V.75A.75.75 0 0 1 4.75 0ZM2.5 7.5v6.75c0 .138.112.25.25.25h10.5a.25.25 0 0 0 .25-.25V7.5Zm10.75-4H2.75a.25.25 0 0 0-.25.25V6h11V3.75a.25.25 0 0 0-.25-.25Z" transform="scale(1.1)"/>
      <text x="25" y="12" class="stat-label">Total Contributions (Year)</text>
      <text x="210" y="12" class="stat-value">{data['total_contributions']}</text>
    </g>

    <g class="streak-row" transform="translate(0, 75)">
      <path class="icon" d="M8 1.25a.75.75 0 0 1 .44.144l2.5 1.833a4.75 4.75 0 0 1 1.81 3.773c0 2.76-2.24 5-5 5s-5-2.24-5-5a4.75 4.75 0 0 1 1.81-3.773l2.5-1.833A.75.75 0 0 1 8 1.25Zm0 2.052L6.155 4.67a3.25 3.25 0 0 0-1.405 2.58C4.75 8.94 6.205 10.25 8 10.25s3.25-1.31 3.25-3A3.25 3.25 0 0 0 9.845 4.67L8 3.302Z" transform="scale(1.1)"/>
      <text x="25" y="12" class="stat-label">Current Streak</text>
      <text x="210" y="12" class="stat-value" fill="#ff7b72">{data['current_streak']} days</text>
    </g>

    <g class="streak-row" transform="translate(0, 115)">
      <path class="icon" d="M2.75 1.5a.25.25 0 0 0-.25.25V3c0 .542.103 1.054.29 1.522L4.04 4.5h-.012c.11.23.242.443.393.65.347.478.784.887 1.289 1.196L5.75 8.5H4v1.5H3v1.5h3v2.25c0 .414.336.75.75.75h2.5a.75.75 0 0 0 .75-.75V13.25h3V11.75h-1V10.25H10.25l.04-.154c.505-.309.942-.718 1.29-1.196.15-.207.282-.42.392-.65h-.012l1.25-1.978A2.99 2.99 0 0 0 13.5 3V1.75a.25.25 0 0 0-.25-.25H2.75zm1.5 1.5h.5V4.5H4.25c-.22 0-.414-.078-.57-.214C3.52 4.146 3.4 3.96 3.32 3.75H4.25zm7.5 0h.93c-.08.21-.2.396-.36.536-.156.136-.35.214-.57.214H11.75V3z" transform="scale(1.1)"/>
      <text x="25" y="12" class="stat-label">Longest Streak</text>
      <text x="210" y="12" class="stat-value">{data['longest_streak']} days</text>
    </g>
  </g>
</svg>
"""
    
    with open(OUTPUT_SVG, "w", encoding="utf-8") as f:
        f.write(svg_content)
    print(f"Successfully generated custom stats SVG at {OUTPUT_SVG}")

if __name__ == "__main__":
    stats_data = fetch_github_stats()
    generate_svg(stats_data)
