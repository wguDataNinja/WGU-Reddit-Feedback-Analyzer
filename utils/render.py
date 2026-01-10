# utils/render.py

import pandas as pd
from IPython.display import display, HTML
from utils.paths import OUTPUT_DIR


def render_table(df, title="Preview Table"):
    df = df.copy()

    # Shorten selftext for readability
    df['selftext'] = df['selftext'].str.slice(0, 300) + '...'

    # Add clickable Reddit permalink
    df['permalink'] = df['permalink'].apply(
        lambda x: f'<a href="https://www.reddit.com{x}" target="_blank">link</a>' if pd.notna(x) else ''
    )

    # Include columns only if they exist
    base_columns = [
        'post_id', 'title', 'selftext', 'text_length',
        'matched_course_codes', 'VADER_Compound', 'permalink'
    ]
    columns = [col for col in base_columns if col in df.columns]
    df = df[columns]

    print(f"[render_table]  Showing {min(len(df), 100)} of {len(df)} total posts")

    styles = """
    <style>
        table { table-layout: auto; width: 100%; }
        td:nth-child(3) { min-width: 300px; max-width: 600px; }
        td:nth-child(4), td:nth-child(5), td:nth-child(6) { white-space: nowrap; width: 1%; }
    </style>
    """

    html = df.head(100).to_html(index=False, escape=False)

    display(HTML(f"""
        {styles}
        <h4>{title}</h4>
        <div style="max-height:500px; overflow:auto; border:1px solid #ccc; padding:10px; font-family:monospace; font-size:12px">
        {html}
        </div>
    """))


def generate_sentiment_spotlight(df, title="Sentiment Spotlight", max_posts=10, sentiment_threshold=-0.3):
    """
    Displays posts with color-coded text highlighting negative sentiment words.

    Args:
        df (DataFrame): DataFrame with 'sentiment_spotlight' column
        title (str): Title for the display
        max_posts (int): Maximum number of posts to display
        sentiment_threshold (float): Threshold for red highlighting (default: -0.3)
    """

    def highlight_words(words_data, text_type="text"):
        """Convert word sentiment data to HTML with color highlighting"""
        if not words_data:
            return f"<em>No {text_type} content</em>"

        html_parts = []
        for word_data in words_data:
            word = word_data['word']
            sentiment = word_data['sentiment']

            if sentiment < sentiment_threshold:
                # Red highlighting for negative words
                html_parts.append(
                    f'<span style="background-color: #ffcccc; color: #cc0000; font-weight: bold;">{word}</span>')
            else:
                html_parts.append(word)

        return ' '.join(html_parts)

    def process_row_for_display(row):
        """Process a row to create highlighted HTML"""
        spotlight_data = row.get('sentiment_spotlight', {})

        # Get word counts for summary
        title_words = spotlight_data.get('title_words', [])
        selftext_words = spotlight_data.get('selftext_words', [])

        title_negative_count = sum(1 for w in title_words if w['sentiment'] < sentiment_threshold)
        selftext_negative_count = sum(1 for w in selftext_words if w['sentiment'] < sentiment_threshold)
        total_negative = title_negative_count + selftext_negative_count

        # Create highlighted HTML
        highlighted_title = highlight_words(title_words, "title")
        highlighted_selftext = highlight_words(selftext_words, "selftext")

        return {
            'post_id': row.get('post_id', 'N/A'),
            'highlighted_title': highlighted_title,
            'highlighted_selftext': highlighted_selftext,
            'negative_words': total_negative,
            'title_negative': title_negative_count,
            'selftext_negative': selftext_negative_count
        }

    # Filter for posts that have sentiment_spotlight data
    valid_posts = df[df['sentiment_spotlight'].notna()].copy()

    if valid_posts.empty:
        print("⚠️ No posts with sentiment_spotlight data found. Run vader_sentiment_spotlight() first.")
        return

    # Process posts for display
    display_data = []
    for _, row in valid_posts.head(max_posts).iterrows():
        display_data.append(process_row_for_display(row))

    # Create display DataFrame
    display_df = pd.DataFrame(display_data)

    # Generate HTML table
    html_rows = []
    for _, row in display_df.iterrows():
        html_rows.append(f"""
        <tr>
            <td style="vertical-align: top; padding: 8px; font-weight: bold; min-width: 80px;">
                {row['post_id']}<br>
                <small style="color: #666;">({row['negative_words']} negative words)</small>
            </td>
            <td style="vertical-align: top; padding: 8px; border-bottom: 1px solid #eee;">
                <strong>Title:</strong><br>
                <div style="margin: 4px 0; line-height: 1.4;">{row['highlighted_title']}</div>
                <br>
                <strong>Content:</strong><br>
                <div style="margin: 4px 0; line-height: 1.4; max-height: 200px; overflow-y: auto;">
                    {row['highlighted_selftext']}
                </div>
            </td>
        </tr>
        """)

    # CSS and HTML structure
    html_content = f"""
    <style>
        .sentiment-spotlight-table {{
            table-layout: fixed;
            width: 100%;
            border-collapse: collapse;
            font-family: Arial, sans-serif;
            font-size: 13px;
        }}
        .sentiment-spotlight-table td {{
            word-wrap: break-word;
            border: 1px solid #ddd;
        }}
        .highlight-negative {{
            background-color: #ffcccc;
            color: #cc0000;
            font-weight: bold;
            padding: 1px 2px;
            border-radius: 2px;
        }}
    </style>

    <h4>{title}</h4>
    <p>Showing {len(display_df)} posts with words highlighted in <span class="highlight-negative">red</span> for sentiment &lt; {sentiment_threshold}</p>

    <div style="max-height: 600px; overflow-y: auto; border: 1px solid #ccc;">
        <table class="sentiment-spotlight-table">
            <thead>
                <tr style="background-color: #f5f5f5;">
                    <th style="padding: 8px; text-align: left; width: 120px;">Post ID</th>
                    <th style="padding: 8px; text-align: left;">Content</th>
                </tr>
            </thead>
            <tbody>
                {''.join(html_rows)}
            </tbody>
        </table>
    </div>
    """

    print(
        f"[generate_sentiment_spotlight] Displaying {len(display_df)} posts with negative sentiment words highlighted")
    display(HTML(html_content))


# Example usage:
"""
# Step 1: Calculate sentiment spotlight
df_with_spotlight = vader_sentiment_spotlight(df_filtered_vader)

# Step 2: Display results
generate_sentiment_spotlight(df_with_spotlight, 
                           title="Reddit Posts - Negative Words Highlighted", 
                           max_posts=5, 
                           sentiment_threshold=-0.3)
"""