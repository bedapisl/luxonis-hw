import math
import base64
from typing import Tuple, Optional
import datetime
from dash import Dash, html, dcc, Input, Output
from dash.exceptions import PreventUpdate
from flats_downloader.spiders.flats_spider import DB_TABLE_NAME, get_cursor, FlatsSpider
import dash_bootstrap_components as dbc
from dash.dependencies import Component
from psycopg2.extensions import cursor
import scrapy
from scrapy.crawler import CrawlerProcess


RECORDS_PER_PAGE = 20


def render_image(image_link: str) -> Component:
    """
    Returns HTML element with the image.
    """
    #return html.Img(src='data:image/png;base64,' + base64.b64encode(image_data).decode('utf-8'))
    return html.Img(src=image_link)


def render_single_flat(flat_data: Tuple[int, datetime.datetime, str, str, str]) -> Component:
    """
    Return HTML element representing a single flat.
    """
    _, _, title, link, image_data = flat_data

    children = []
    title = html.Div(title)
    link = dcc.Link(link, href=link, refresh=True)
    image = render_image(image_data)

    return dbc.Container(dbc.Card(children=[dbc.CardBody(children=[image, title, link])]))


def render_page(page_index: int, cursor: cursor) -> Component:
    """
    Gets flat data from database (using the provided cursor) and return HTML element for all flats in one page
    """
    # We want to show newest data from our database, so find the newest timestamp
    cursor.execute(f"SELECT Max(Timestamp) FROM {DB_TABLE_NAME}")
    newest_timestamp = cursor.fetchone()[0]

    # RecordID are consecutive integers corresponding to the order in which the flats were added to database
    # Find index where the records with newest index start.
    cursor.execute(f"SELECT Min(RecordID) FROM {DB_TABLE_NAME} WHERE Timestamp = '{newest_timestamp}'")
    smallest_index = cursor.fetchone()[0]

    index_min = smallest_index + page_index * RECORDS_PER_PAGE

    # Get data which should be on the current page
    cursor.execute(f"SELECT * FROM {DB_TABLE_NAME} WHERE Timestamp = '{newest_timestamp}' AND RecordID >= {index_min} ORDER BY RecordID ASC LIMIT {RECORDS_PER_PAGE}")
    data = cursor.fetchall()

    children = []
    for flat_data in data:
        children.append(render_single_flat(flat_data))

    return html.Div(children, id="main_page")


def render_full(page_index: int, cursor: cursor) -> Component:
    """
    Returns HTML element representing whole page.
    """
    main_page = render_page(page_index, cursor)

    # Find out how many pages will be there - we are showing only flats with the newest timestamp
    cursor.execute(f"SELECT Count(*) FROM {DB_TABLE_NAME} WHERE Timestamp = (SELECT Max(Timestamp) FROM {DB_TABLE_NAME})")
    flats = cursor.fetchone()[0]
    pages = math.ceil(flats / RECORDS_PER_PAGE)

    pagination = dbc.Pagination(id="pagination", max_value=pages)
    return html.Div(children=[main_page, pagination])


def create_callbacks(cursor: cursor) -> None:
    """
    Define all Dash callbacks here.
    """

    @app.callback(
        Output("main_page", "children"),
        [Input("pagination", "active_page")],
    )
    def change_page(page: Optional[int]) -> Component:
        """
        Callback which fires when page is changed, renders the new page.

        Args:
            page: Dash provides None for the initial callback, integer with new page index otherwise
        """
        if not page:  # Do nothing on initial callback
            raise PreventUpdate

        return render_page(page - 1, cursor)  # Use -1 because first page on frontend has index 1, but we start from 0


def start_downloading():
    """
    Starts downloading of current newest data
    """
    process = CrawlerProcess({
        'USER_AGENT': 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1)'
    })
       
    process.crawl(FlatsSpider)
    process.start()


if __name__ == '__main__':
    start_downloading()
    app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
    connection, cursor = get_cursor()
    create_callbacks(cursor)
    app.layout = render_full(0, cursor)
    app.run_server(debug=True, port=8080)
