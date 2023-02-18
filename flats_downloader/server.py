import math
import base64
from dash import Dash, html, dcc, Input, Output
from dash.exceptions import PreventUpdate
from flats_downloader.spiders.flats_spider import DB_TABLE_NAME, get_cursor
import dash_bootstrap_components as dbc

RECORDS_PER_PAGE = 20


def render_image(image_data):
    return html.Img(src='data:image/png;base64,' + base64.b64encode(image_data).decode('utf-8'))


def render_single_flat(flat_data):
    _, _, title, link, image_data = flat_data

    children = []
    title = html.Div(title)
    link = dcc.Link(link, href=link, refresh=True)
    image = render_image(image_data)

    return html.Div(children=[title, link, image])


def render_page(page_index, cursor):
    cursor.execute(f"SELECT Max(Timestamp) FROM {DB_TABLE_NAME}")
    newest_timestamp = cursor.fetchone()[0]

    cursor.execute(f"SELECT Min(RecordID) FROM {DB_TABLE_NAME} WHERE Timestamp = '{newest_timestamp}'")
    smallest_index = cursor.fetchone()[0]

    index_min = smallest_index + page_index * RECORDS_PER_PAGE
    
    cursor.execute(f"SELECT * FROM {DB_TABLE_NAME} WHERE Timestamp = '{newest_timestamp}' AND RecordID >= {index_min} ORDER BY RecordID ASC LIMIT {RECORDS_PER_PAGE}")
    data = cursor.fetchall()

    children = []
    for flat_data in data:
        children.append(render_single_flat(flat_data))

    return html.Div(children, id="main_page")


def render_full(page_index, cursor):
    main_page = render_page(page_index, cursor)
    
    cursor.execute(f"SELECT Count(*) FROM {DB_TABLE_NAME} WHERE Timestamp = (SELECT Max(Timestamp) FROM {DB_TABLE_NAME})")
    flats = cursor.fetchone()[0]
    pages = math.ceil(flats / RECORDS_PER_PAGE)

    pagination = dbc.Pagination(id="pagination", max_value=pages)
    return html.Div(children=[main_page, pagination])


def create_callbacks(cursor):
    @app.callback(
        Output("main_page", "children"),
        [Input("pagination", "active_page")],
    )
    def change_page(page):
        if not page:
            raise PreventUpdate

        return render_page(page - 1, cursor)


if __name__ == '__main__':
    app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
    connection, cursor = get_cursor()
    create_callbacks(cursor)
    app.layout = render_full(0, cursor)
    app.run_server(debug=True, port=8080)
