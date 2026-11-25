"""
StayHome - Web server (pure Python, standard library only)
----------------------------------------------------------
Run:   python app.py          then open  http://localhost:8000

How the website asks Python to run:
  1. The page (index.html) sends a request, e.g.  POST /api/book_room
  2. This server finds the matching function in hotel.py and calls it.
  3. The function returns (ok, message). If ok, the data is saved to hotel_data.json.
  4. The server sends the answer back, and the page shows it.

All hotel rules live in hotel.py. This file only connects the web page to them.
"""

import json
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

import hotel

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)                                        # data and CSV files are saved next to app.py
hotel.DATA_FILE = os.path.join(HERE, "hotel_data.json")


def reset(data):
    data.clear()
    data.update(hotel.seed_data())
    return True, "Demo data reset."


# Button name  ->  Python function that does the work
ACTIONS = {
    "add_room": hotel.add_room,
    "add_room_type": hotel.add_room_type,
    "set_room_status": hotel.set_room_status,
    "delete_room": hotel.delete_room,
    "add_customer": hotel.add_customer,
    "delete_customer": hotel.delete_customer,
    "book_room": hotel.book_room,
    "check_in_guest": hotel.check_in_guest,
    "take_payment": hotel.take_payment,
    "check_out_guest": hotel.check_out_guest,
    "cancel_booking": hotel.cancel_booking,
    "reset": reset,
}


class Handler(BaseHTTPRequestHandler):

    def reply(self, code, body, content_type="application/json", extra_headers=None):
        if not isinstance(body, bytes):
            body = json.dumps(body).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        for name, value in (extra_headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)

    # ---------- GET: the page and read-only information ----------
    def do_GET(self):
        path = self.path.split("?")[0]
        try:
            if path == "/":
                with open(os.path.join(HERE, "index.html"), "rb") as file:
                    self.reply(200, file.read(), "text/html; charset=utf-8")

            elif path == "/api/data":
                data = hotel.load_data()
                self.reply(200, {**data, "summary": hotel.dashboard(data)})

            elif path.startswith("/api/invoice/"):
                ok, text = hotel.make_invoice(hotel.load_data(), int(path.split("/")[-1]))
                self.reply(200, {"ok": ok, "message": text})

            elif path.startswith("/api/export/"):
                kind = path.split("/")[-1]
                ok, message = hotel.export_csv(hotel.load_data(), kind)   # Python writes the .csv file
                if not ok:
                    self.reply(400, {"ok": False, "message": message})
                else:
                    filename = f"stayhome_{kind}.csv"
                    with open(os.path.join(HERE, filename), "rb") as file:
                        self.reply(200, file.read(), "text/csv; charset=utf-8",
                                   {"Content-Disposition": f"attachment; filename={filename}"})
            else:
                self.reply(404, {"ok": False, "message": "Not found."})
        except Exception as error:
            print("Error:", error)
            self.reply(400, {"ok": False, "message": "Invalid request."})

    # ---------- POST: every button that changes something ----------
    def do_POST(self):
        action = self.path.split("/")[-1]
        if action not in ACTIONS:
            self.reply(404, {"ok": False, "message": "Unknown action."})
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            args = json.loads(self.rfile.read(length) or "[]")       # list of inputs from the page
            data = hotel.load_data()
            ok, message = ACTIONS[action](data, *args)               # <-- the page asks Python to run this
            if ok:
                hotel.save_data(data)
            self.reply(200, {"ok": ok, "message": message})
        except Exception as error:
            print("Error:", error)
            self.reply(400, {"ok": False, "message": "Invalid input. Please check the values."})


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    hotel.save_data(hotel.load_data())                # creates hotel_data.json on first run
    server = HTTPServer(("127.0.0.1", port), Handler)
    print(f"StayHome is running. Open http://localhost:{port} in your browser.")
    print("Every request from the page will be printed below. Press Ctrl+C to stop.\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
