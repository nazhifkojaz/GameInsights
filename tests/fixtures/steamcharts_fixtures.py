"""Fixtures for SteamCharts source tests."""

import pytest


@pytest.fixture
def steamcharts_success_response_data():
    """Success HTML response for SteamCharts."""
    data = """
    <!DOCTYPE html>

    <html lang="en">
    <head>
    <meta charset="utf-8"/>
    <title>Mock Game - Steam Charts</title>
    </head>
    <body>
    <h1 id="app-title"><a href="">Mock Game: The Adventure</a></h1>
    <div class="app-stat">
    <span class="num">1234</span>
    <br/>playing <abbr class="timeago" title="1234-05-06T07:08:09Z"></abbr>
    </div>
    <div class="app-stat">
    <span class="num">4321</span>
    <br/>24-hour peak
        </div>
    <div class="app-stat">
    <span class="num">12345</span>
    <br/>all-time peak
        </div>
    </div>
    <div class="content">
    <table class="common-table">
    <thead>
    <tr>
    <th class="left">Month</th>
    <th class="right">Avg. Players</th>
    <th class="right">Gain</th>
    <th class="right">% Gain</th>
    <th class="right">Peak Players</th>
    </tr>
    </thead>
    <tbody>
    <tr class="odd">
    <td class="month-cell left italic">Last 30 Days</td>
    <td class="right num-f italic">123.45</td>
    <td class="right num-p gainorloss italic">-12.34</td>
    <td class="right gainorloss italic">-12.34%</td>
    <td class="right num italic">1234</td>
    </tr>
    <tr>
    <td class="month-cell left">June 1234</td>
    <td class="right num-f">123.45</td>
    <td class="right num-p gainorloss">12.34</td>
    <td class="right gainorloss">+12.34%</td>
    <td class="right num">12345</td>
    </tr>
    </tbody>
    </table>
    </div>
    </body>
    </html>
    """
    return data


@pytest.fixture
def steamcharts_error_response_no_app_title():
    """Error response when game title is not found."""
    data = """
    <!DOCTYPE html>

    <html lang="en">
    <head>
    <meta charset="utf-8"/>
    <title>Mock Game - Steam Charts</title>
    </head>
    <body>
    </div>
    </body>
    </html>
    """
    return data


@pytest.fixture
def steamcharts_error_response_incorrect_appstat_count():
    """Error response when there are too few app-stat divs."""
    data = """
    <!DOCTYPE html>

    <html lang="en">
    <head>
    <meta charset="utf-8"/>
    <title>Mock Game - Steam Charts</title>
    </head>
    <body>
    <h1 id="app-title"><a href="">Mock Game: The Adventure</a></h1>
    <div class="app-stat">
    <span class="num">1234</span>
    <br/>playing <abbr class="timeago" title="1234-05-06T07:08:09Z"></abbr>
    </div>
    </body>
    </html>
    """
    return data


@pytest.fixture
def steamcharts_error_response_incorrect_appstat_structure():
    """Error response when app-stat has incorrect structure."""
    data = """
    <!DOCTYPE html>

    <html lang="en">
    <head>
    <meta charset="utf-8"/>
    <title>Mock Game - Steam Charts</title>
    </head>
    <body>
    <h1 id="app-title"><a href="">Mock Game: The Adventure</a></h1>
    <div class="app-stat">
    <span class="str">1234</span>
    <br/>playing <abbr class="timeago" title="1234-05-06T07:08:09Z"></abbr>
    </div>
    <div class="app-stat">
    <span class="str">4321</span>
    <br/>24-hour peak
        </div>
    <div class="app-stat">
    <span class="str">12345</span>
    <br/>all-time peak
        </div>
    </div>
    </body>
    </html>
    """
    return data


@pytest.fixture
def steamcharts_error_response_no_player_data_table():
    """Error response when player data table is missing."""
    data = """
    <!DOCTYPE html>

    <html lang="en">
    <head>
    <meta charset="utf-8"/>
    <title>Mock Game - Steam Charts</title>
    </head>
    <body>
    <h1 id="app-title"><a href="">Mock Game: The Adventure</a></h1>
    <div class="app-stat">
    <span class="num">1234</span>
    <br/>playing <abbr class="timeago" title="1234-05-06T07:08:09Z"></abbr>
    </div>
    <div class="app-stat">
    <span class="num">4321</span>
    <br/>24-hour peak
        </div>
    <div class="app-stat">
    <span class="num">12345</span>
    <br/>all-time peak
        </div>
    </div>
    </body>
    </html>
    """
    return data


@pytest.fixture
def steamcharts_error_response_player_data_table_incorrect_structure():
    """Error response when player data table has wrong structure."""
    data = """
    <!DOCTYPE html>

    <html lang="en">
    <head>
    <meta charset="utf-8"/>
    <title>Mock Game - Steam Charts</title>
    </head>
    <body>
    <h1 id="app-title"><a href="">Mock Game: The Adventure</a></h1>
    <div class="app-stat">
    <span class="num">1234</span>
    <br/>playing <abbr class="timeago" title="1234-05-06T07:08:09Z"></abbr>
    </div>
    <div class="app-stat">
    <span class="num">4321</span>
    <br/>24-hour peak
        </div>
    <div class="app-stat">
    <span class="num">12345</span>
    <br/>all-time peak
        </div>
    </div>
    <div class="content">
    <table class="common-table">
    <thead>
    <tr>
    <th class="left">Month</th>
    <th class="right">Avg. Players</th>
    <th class="right">Gain</th>
    <th class="right">% Gain</th>
    </tr>
    </thead>
    <tbody>
    <tr class="odd">
    <td class="month-cell left italic">Last 30 Days</td>
    <td class="right num-f italic">123.45</td>
    <td class="right num-p gainorloss italic">-12.34</td>
    <td class="right gainorloss italic">-12.34%</td>
    </tr>
    <tr>
    <td class="month-cell left">June 1234</td>
    <td class="right num-f">123.45</td>
    <td class="right num-p gainorloss">12.34</td>
    <td class="right gainorloss">+12.34%</td>
    </tr>
    </tbody>
    </table>
    </div>
    </body>
    </html>
    """
    return data


@pytest.fixture
def steamcharts_malformed_row_response_data():
    """HTML response with a malformed row (3 cells instead of 5) to test row validation."""
    data = """
    <!DOCTYPE html>
    <html>
    <body>
        <h1 id="app-title">Test Game</h1>
        <div class="app-stat"><span class="num">1000</span></div>
        <div class="app-stat"><span class="num">2000</span></div>
        <div class="app-stat"><span class="num">3000</span></div>
        <table class="common-table">
            <tr><th>Last 30 Days</th><th></th><th></th><th></th><th></th></tr>
            <tr><th>Month</th><th>Avg. Players</th><th>Gain</th><th>% Gain</th><th>Peak</th></tr>
            <tr><td>January 2025</td><td>1000</td><td>+100</td><td>+10%</td><td>2000</td></tr>
            <tr><td>February 2025</td><td>1200</td><td>+200</td></tr>  <!-- Malformed: only 3 cells -->
            <tr><td>March 2025</td><td>1500</td><td>+300</td><td>+15%</td><td>3000</td></tr>
        </table>
    </body>
    </html>
    """
    return data
