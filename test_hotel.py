"""
Tests for hotel.py  -  run with:  python test_hotel.py
Uses only plain assert statements. Works in a temporary folder, so your real data is never touched.
"""

import os
import tempfile
from datetime import date, timedelta

import hotel


def days(n):
    """Date text for 'n days from today'."""
    return str(date.today() + timedelta(days=n))


def check(condition, message):
    assert condition, "FAILED: " + message
    print("  OK  " + message)


def run():
    os.chdir(tempfile.mkdtemp())
    data = hotel.seed_data()

    print("\n1. Booking and bill")
    ok, msg = hotel.book_room(data, 1, 3, days(10), days(13), 2, 400, 2000)   # Room 201: Rs 2800 x 3 nights
    b1 = data["bookings"][0]
    check(ok, "valid booking is accepted")
    check(b1["room_charges"] == 8400 and b1["tax"] == 800 and b1["total"] == 8800, "bill = 8400 - 400 + 10% tax = 8800")
    check(hotel.payment_status(b1) == "Partially Paid", "Rs 2000 advance -> Partially Paid")

    print("\n2. Double booking")
    check(not hotel.book_room(data, 2, 3, days(11), days(14), 1, 0, 0)[0], "overlapping dates are rejected")
    check(hotel.book_room(data, 2, 3, days(13), days(15), 1, 0, 0)[0], "same-day turnover (leave 13th, arrive 13th) is allowed")

    print("\n3. Validation")
    check(not hotel.book_room(data, 1, 5, days(-1), days(2), 1, 0, 0)[0], "check-in in the past is rejected")
    check(not hotel.book_room(data, 1, 5, days(8), days(5), 1, 0, 0)[0], "check-out before check-in is rejected")
    check(not hotel.book_room(data, 1, 5, "tomorrow", days(5), 1, 0, 0)[0], "bad date text is rejected")
    check(not hotel.book_room(data, 1, 3, days(30), days(32), 4, 0, 0)[0], "4 guests in a 3-guest room is rejected")
    check(not hotel.book_room(data, 1, 4, days(30), days(32), 1, 0, 0)[0], "maintenance room cannot be booked")
    check(not hotel.book_room(data, 1, 5, days(30), days(32), 1, -100, 0)[0], "negative discount is rejected")

    print("\n4. Check-in and check-out")
    check(hotel.check_in_guest(data, 1)[0], "check-in works")
    check(data["rooms"][2]["status"] == "Occupied", "room becomes Occupied")
    check(not hotel.check_in_guest(data, 2)[0], "second guest cannot check in to an Occupied room")
    check(not hotel.check_out_guest(data, 1)[0], "check-out is refused while balance is unpaid")
    check(not hotel.take_payment(data, 1, 99999)[0], "overpayment is rejected")
    check(hotel.take_payment(data, 1, 6800)[0], "paying the balance works")
    check(hotel.check_out_guest(data, 1)[0], "check-out works after full payment")
    check(data["rooms"][2]["status"] == "Available", "room is Available again")
    check(hotel.check_in_guest(data, 2)[0], "next guest can now check in")

    print("\n5. Cancel")
    hotel.book_room(data, 3, 5, days(20), days(22), 2, 0, 1000)
    check(hotel.cancel_booking(data, 3)[0], "confirmed booking can be cancelled")
    check(data["bookings"][2]["paid"] == 0, "advance is refunded (paid set to 0)")
    check(hotel.book_room(data, 3, 5, days(20), days(22), 2, 0, 0)[0], "cancelled dates become free again")
    check(not hotel.cancel_booking(data, 1)[0], "a checked-out booking cannot be cancelled")

    print("\n6. Safe deletion")
    check(not hotel.delete_room(data, 3)[0], "room with booking history cannot be deleted")
    check(not hotel.delete_customer(data, 1)[0], "customer with booking history cannot be deleted")
    hotel.add_room(data, "999", "suite", 6000, 4)
    check(hotel.delete_room(data, 7)[0], "a new room with no bookings can be deleted")

    print("\n7. Duplicates and input checks")
    check(not hotel.add_room(data, "101", "Standard", 1500, 2)[0], "duplicate room number is rejected")
    check(not hotel.add_room(data, "500", "Palace", 1500, 2)[0], "unknown room type is rejected")
    check(hotel.add_room_type(data, " family ")[0], "a new room type can be created")
    check(not hotel.add_room_type(data, "FAMILY")[0], "duplicate room type is rejected")
    check(hotel.add_room(data, "500", "family", 3000, 4)[0], "a room can use the new type")
    check(not hotel.add_customer(data, "Test Guest", "AARAV@example.com", "9999999999")[0], "duplicate email (any case) is rejected")
    check(not hotel.add_customer(data, "Test Guest", "not-an-email", "9999999999")[0], "invalid email is rejected")
    check(hotel.add_customer(data, "Test Guest", " New@Example.com ", "99999 99999")[0], "valid customer is added")

    print("\n8. Reports, files")
    ok, text = hotel.make_invoice(data, 1)
    check(ok and "Rs 8800" in text and "Paid" in text, "invoice shows total and Paid status")
    check(hotel.dashboard(data)["Money collected (Rs)"] == 8800, "dashboard revenue is correct")
    hotel.DATA_FILE = "test_data.json"
    hotel.save_data(data)
    check(hotel.load_data() == data, "save then load gives the same data")
    ok, msg = hotel.export_csv(data, "rooms")
    check(ok and open("stayhome_rooms.csv").readline().startswith("id,"), "CSV file is written with a header row")

    print("\nALL TESTS PASSED")


if __name__ == "__main__":
    run()
