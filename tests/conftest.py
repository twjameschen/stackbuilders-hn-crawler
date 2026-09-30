import pytest
import requests


@pytest.fixture
def homepage_response():
    """Synthetic 30-row HTML for offline HTTP/parser/filter/storage integration."""
    specs = [
        (9, "Café 你好 😀", 2, 100),
        (7, "one two three four five six", 100, 2),
        (3, "Short title", 10, 0),
        (2, "a b c d e f", 1, 10),
        *[(n, f"Story {n}", 0, 0) for n in range(10, 36)],
    ]
    rows = []
    for number, title, points, comments in specs:
        item_id = 2000 + number
        rows.append(f'''
            <tr class="athing" id="{item_id}"><td><span class="rank">{number}.</span></td>
            <td class="votelinks"></td><td><span class="titleline"><a>{title}</a></span></td></tr>
            <tr><td colspan="2"></td><td class="subtext"><span class="subline">
            <span class="score" id="score_{item_id}">{points} points</span>
            <span class="age"><a href="item?id={item_id}">1 hour ago</a></span>
            <a href="item?id={item_id}">{comments} comments</a></span></td></tr>
        ''')
    response = requests.Response()
    response.status_code = 200
    response._content = ("<table>" + "".join(rows) + "</table>").encode("utf-8")
    response._content_consumed = True
    return response
