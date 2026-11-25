"""
StayHome - Simple Hotel Management System
-----------------------------------------
Pure Python. No installs needed.      Run:  python hotel.py

How it works (3 ideas):
  1. All data lives in ONE dictionary:  {"rooms": [...], "customers": [...], "bookings": [...]}
     Each room / customer / booking is a small dictionary.
  2. Every action is a function that returns a tuple:  (True/False, "message")
  3. The data is saved to a file (hotel_data.json) after every successful action.
"""

import csv
import json
import os
from datetime import date

DATA_FILE = "hotel_data.json"
TAX_PERCENT = 10

# A tuple (cannot change) and sets (fast "is this allowed?" checks)
ACTIVE_STATUSES = ("Confirmed", "Checked-In")
ROOM_TYPES = {"Standard", "Deluxe", "Suite"}
MANUAL_STATUSES = {"Available", "Maintenance"}
EXPORT_KINDS = ("rooms", "customers", "bookings")


# ============================================================
# PART 1: SAVING AND LOADING DATA  (file handling)
# ============================================================

def seed_data():
    """Starting data used the first time the program runs."""
    rooms = [
        {"id": 1, "number": "101", "type": "Standard", "price": 1500, "capacity": 2, "status": "Available"},
        {"id": 2, "number": "102", "type": "Standard", "price": 1500, "capacity": 2, "status": "Available"},
        {"id": 3, "number": "201", "type": "Deluxe", "price": 2800, "capacity": 3, "status": "Available"},
        {"id": 4, "number": "202", "type": "Deluxe", "price": 2800, "capacity": 2, "status": "Maintenance"},
        {"id": 5, "number": "301", "type": "Suite", "price": 5500, "capacity": 4, "status": "Available"},
        {"id": 6, "number": "302", "type": "Suite", "price": 5500, "capacity": 4, "status": "Available"},
    ]
    customers = [
        {"id": 1, "name": "Aarav Sharma", "email": "aarav@example.com", "phone": "9876543210"},
        {"id": 2, "name": "Priya Nair", "email": "priya@example.com", "phone": "9823011223"},
        {"id": 3, "name": "Rohan Deshmukh", "email": "rohan@example.com", "phone": "9765432109"},
    ]
    return {"rooms": rooms, "customers": customers, "bookings": [], "types": sorted(ROOM_TYPES)}


def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE) as file:
            data = json.load(file)
        data.setdefault("types", sorted(ROOM_TYPES))     # older data files have no types yet
        return data
    return seed_data()


def save_data(data):
    with open(DATA_FILE, "w") as file:
        json.dump(data, file, indent=2)


# ============================================================
# PART 2: SMALL HELPER FUNCTIONS
# ============================================================

def find(records, record_id):
    """Return the record with this id, or None."""
    for record in records:
        if record["id"] == record_id:
            return record
    return None


def next_id(records):
    return max([r["id"] for r in records], default=0) + 1   # list comprehension


def parse_date(text):
    """'2026-12-25' -> date object.  Returns None if the text is not a valid date."""
    try:
        return date.fromisoformat(text.strip())
    except ValueError:
        return None


def calculate_bill(nights, price, discount):
    """All money is in whole rupees (int), so there are no decimal rounding errors."""
    room_charges = nights * price
    discount = min(discount, room_charges)          # discount can never exceed the charges
    taxable = room_charges - discount
    tax = taxable * TAX_PERCENT // 100
    return {"room_charges": room_charges, "discount": discount, "tax": tax, "total": taxable + tax}


def payment_status(booking):
    if booking["paid"] >= booking["total"]:
        return "Paid"
    elif booking["paid"] > 0:
        return "Partially Paid"
    else:
        return "Pending"


def is_room_free(data, room_id, check_in, check_out):
    """
    DOUBLE-BOOKING CHECK (interval overlap rule):
    An old booking clashes with the new dates if
        old_check_in < new_check_out   AND   old_check_out > new_check_in
    """
    for b in data["bookings"]:
        if b["room_id"] == room_id and b["status"] in ACTIVE_STATUSES:
            old_in = date.fromisoformat(b["check_in"])
            old_out = date.fromisoformat(b["check_out"])
            if old_in < check_out and old_out > check_in:
                return False
    return True


# ============================================================
# PART 3: HOTEL ACTIONS  (each returns (True/False, message))
# ============================================================

# ---------- Rooms ----------

def add_room(data, number, room_type, price, capacity):
    number = number.strip()
    room_type = room_type.strip().title()
    if number == "":
        return False, "Room number is required."
    if room_type not in data["types"]:
        return False, "Room type must be one of: " + ", ".join(data["types"]) + "."
    if price <= 0:
        return False, "Price must be more than 0."
    if capacity < 1 or capacity > 10:
        return False, "Capacity must be between 1 and 10."
    if any(r["number"] == number for r in data["rooms"]):
        return False, f"Room {number} already exists."
    data["rooms"].append({"id": next_id(data["rooms"]), "number": number, "type": room_type,
                          "price": price, "capacity": capacity, "status": "Available"})
    return True, f"Room {number} added."


def add_room_type(data, name):
    name = " ".join(name.split()).title()           # tidy spaces, Capitalize Words
    if len(name) < 2:
        return False, "Type name is too short."
    if name in data["types"]:
        return False, f"Room type {name} already exists."
    data["types"].append(name)
    return True, f"Room type {name} created."


def set_room_status(data, room_id, status):
    room = find(data["rooms"], room_id)
    status = status.strip().title()
    if room is None:
        return False, "Room not found."
    if status not in MANUAL_STATUSES:
        return False, "Status must be Available or Maintenance."
    if room["status"] == "Occupied":
        return False, "A guest is staying in this room. Check them out first."
    room["status"] = status
    return True, f"Room {room['number']} is now {status}."


def delete_room(data, room_id):
    room = find(data["rooms"], room_id)
    if room is None:
        return False, "Room not found."
    if any(b["room_id"] == room_id for b in data["bookings"]):
        return False, "This room has booking history, so it cannot be deleted."
    data["rooms"].remove(room)
    return True, f"Room {room['number']} deleted."


# ---------- Customers ----------

def add_customer(data, name, email, phone):
    name = name.strip()
    email = email.strip().lower()
    phone = phone.strip()
    digits = [ch for ch in phone if ch.isdigit()]   # list comprehension
    if len(name) < 2:
        return False, "Name is too short."
    if "@" not in email or "." not in email.split("@")[-1]:
        return False, "Please enter a valid email."
    if len(digits) < 7:
        return False, "Phone number needs at least 7 digits."
    if any(c["email"] == email for c in data["customers"]):
        return False, "A customer with this email already exists."
    data["customers"].append({"id": next_id(data["customers"]), "name": name,
                              "email": email, "phone": phone})
    return True, f"Customer {name} registered."


def delete_customer(data, customer_id):
    customer = find(data["customers"], customer_id)
    if customer is None:
        return False, "Customer not found."
    if any(b["customer_id"] == customer_id for b in data["bookings"]):
        return False, "This customer has booking history, so they cannot be deleted."
    data["customers"].remove(customer)
    return True, f"Customer {customer['name']} deleted."


# ---------- Bookings ----------

def book_room(data, customer_id, room_id, check_in_text, check_out_text, guests, discount, advance):
    customer = find(data["customers"], customer_id)
    room = find(data["rooms"], room_id)
    check_in = parse_date(check_in_text)
    check_out = parse_date(check_out_text)

    # Step 1: validate everything before changing any data
    if customer is None:
        return False, "Customer not found."
    if room is None:
        return False, "Room not found."
    if check_in is None or check_out is None:
        return False, "Dates must look like 2026-12-25."
    if check_in < date.today():
        return False, "Check-in date cannot be in the past."
    if check_in >= check_out:
        return False, "Check-out must be after check-in."
    if room["status"] == "Maintenance":
        return False, f"Room {room['number']} is under maintenance."
    if discount < 0 or advance < 0:
        return False, "Discount and advance cannot be negative."
    if guests < 1 or guests > room["capacity"]:
        return False, f"Room {room['number']} holds 1 to {room['capacity']} guests."
    if not is_room_free(data, room_id, check_in, check_out):
        return False, f"Room {room['number']} is already booked for those dates."

    # Step 2: calculate the bill
    nights = (check_out - check_in).days            # date - date = timedelta; .days = number
    bill = calculate_bill(nights, room["price"], discount)
    advance = min(advance, bill["total"])

    # Step 3: save the booking
    booking_id = next_id(data["bookings"])
    code = f"SH-{1000 + booking_id}"
    data["bookings"].append({
        "id": booking_id, "code": code,
        "customer_id": customer_id, "room_id": room_id,
        "check_in": str(check_in), "check_out": str(check_out),
        "nights": nights, "guests": guests, "status": "Confirmed",
        "room_charges": bill["room_charges"], "discount": bill["discount"],
        "tax": bill["tax"], "total": bill["total"], "paid": advance,
    })
    return True, f"Booking {code} confirmed: {nights} night(s), total Rs {bill['total']}."


def check_in_guest(data, booking_id):
    booking = find(data["bookings"], booking_id)
    if booking is None:
        return False, "Booking not found."
    if booking["status"] != "Confirmed":
        return False, f"Cannot check in. This booking is {booking['status']}."
    room = find(data["rooms"], booking["room_id"])
    if room["status"] != "Available":
        return False, f"Room {room['number']} is {room['status']}, so it is not ready."
    booking["status"] = "Checked-In"
    room["status"] = "Occupied"
    return True, f"Checked in. Room {room['number']} is now Occupied."


def take_payment(data, booking_id, amount):
    booking = find(data["bookings"], booking_id)
    if booking is None:
        return False, "Booking not found."
    if booking["status"] not in ACTIVE_STATUSES:
        return False, "Payments can only be taken for active bookings."
    balance = booking["total"] - booking["paid"]
    if amount <= 0:
        return False, "Amount must be more than 0."
    if amount > balance:
        return False, f"Amount is more than the balance (Rs {balance})."
    booking["paid"] += amount
    return True, f"Received Rs {amount}. Balance now Rs {balance - amount}."


def check_out_guest(data, booking_id):
    booking = find(data["bookings"], booking_id)
    if booking is None:
        return False, "Booking not found."
    if booking["status"] != "Checked-In":
        return False, "Only a Checked-In guest can check out."
    balance = booking["total"] - booking["paid"]
    if balance > 0:
        return False, f"Balance of Rs {balance} is unpaid. Take payment first."
    booking["status"] = "Checked-Out"
    find(data["rooms"], booking["room_id"])["status"] = "Available"
    return True, "Checked out. Room is Available again."


def cancel_booking(data, booking_id):
    booking = find(data["bookings"], booking_id)
    if booking is None:
        return False, "Booking not found."
    if booking["status"] != "Confirmed":
        return False, "Only a Confirmed booking can be cancelled."
    refund = booking["paid"]
    booking["status"] = "Cancelled"
    booking["paid"] = 0
    return True, f"Booking {booking['code']} cancelled. Refund Rs {refund} to the guest."


# ---------- Reports ----------

def dashboard(data):
    rooms = data["rooms"]
    bookings = data["bookings"]
    today = str(date.today())
    return {
        "Total rooms": len(rooms),
        "Available rooms": len([r for r in rooms if r["status"] == "Available"]),
        "Occupied rooms": len([r for r in rooms if r["status"] == "Occupied"]),
        "Under maintenance": len([r for r in rooms if r["status"] == "Maintenance"]),
        "Customers": len(data["customers"]),
        "Active bookings": len([b for b in bookings if b["status"] in ACTIVE_STATUSES]),
        "Arriving today": len([b for b in bookings if b["check_in"] == today and b["status"] == "Confirmed"]),
        "Leaving today": len([b for b in bookings if b["check_out"] == today and b["status"] == "Checked-In"]),
        "Money collected (Rs)": sum(b["paid"] for b in bookings),
    }


def make_invoice(data, booking_id):
    booking = find(data["bookings"], booking_id)
    if booking is None:
        return False, "Booking not found."
    customer = find(data["customers"], booking["customer_id"])
    room = find(data["rooms"], booking["room_id"])
    lines = [
        "=" * 42,
        "         STAYHOME HOTEL - INVOICE",
        "=" * 42,
        f"Booking code : {booking['code']}",
        f"Guest        : {customer['name']}",
        f"Room         : {room['number']} ({room['type']})",
        f"Stay         : {booking['check_in']} to {booking['check_out']} ({booking['nights']} nights)",
        "-" * 42,
        f"Room charges : Rs {booking['room_charges']}",
        f"Discount     : - Rs {booking['discount']}",
        f"Tax ({TAX_PERCENT}%)     : Rs {booking['tax']}",
        f"TOTAL        : Rs {booking['total']}",
        f"Paid         : Rs {booking['paid']}",
        f"Balance due  : Rs {booking['total'] - booking['paid']}",
        f"Status       : {payment_status(booking)}",
        "=" * 42,
    ]
    return True, "\n".join(lines)


def export_csv(data, kind):
    """Write rooms / customers / bookings to a real .csv file (file handling)."""
    if kind not in EXPORT_KINDS:
        return False, "Choose rooms, customers or bookings."
    rows = data[kind]
    if not rows:
        return False, f"There are no {kind} to export."
    filename = f"stayhome_{kind}.csv"
    with open(filename, "w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return True, f"Saved {len(rows)} row(s) to {filename}"


# ============================================================
# PART 4: SCREEN OUTPUT AND KEYBOARD INPUT
# ============================================================

def show_rooms(data):
    print(f"\n{'ID':<4}{'Room':<7}{'Type':<10}{'Price':<8}{'Guests':<8}Status")
    for r in data["rooms"]:
        print(f"{r['id']:<4}{r['number']:<7}{r['type']:<10}{r['price']:<8}{r['capacity']:<8}{r['status']}")


def show_customers(data):
    print(f"\n{'ID':<4}{'Name':<20}{'Email':<26}Phone")
    for c in data["customers"]:
        print(f"{c['id']:<4}{c['name']:<20}{c['email']:<26}{c['phone']}")


def show_bookings(data):
    print(f"\n{'ID':<4}{'Code':<10}{'Guest':<18}{'Room':<6}{'Check-in':<12}{'Check-out':<12}{'Status':<12}{'Payment'}")
    for b in data["bookings"]:
        guest = find(data["customers"], b["customer_id"])["name"]
        room = find(data["rooms"], b["room_id"])["number"]
        print(f"{b['id']:<4}{b['code']:<10}{guest:<18}{room:<6}{b['check_in']:<12}{b['check_out']:<12}"
              f"{b['status']:<12}{payment_status(b)}")
    if not data["bookings"]:
        print("(no bookings yet)")


def ask_text(prompt):
    return input(prompt).strip()


def ask_number(prompt):
    """Keep asking until the user types a whole number."""
    while True:
        text = input(prompt).strip()
        if text.isdigit():
            return int(text)
        print("Please type a whole number (0 or more).")


def report(result, data):
    """Print the message from an action. Save the data only if it worked."""
    ok, message = result
    print(("OK: " if ok else "ERROR: ") + message)
    if ok:
        save_data(data)


MENU = """
========== STAYHOME HOTEL ==========
 1  Dashboard
 2  Show rooms
 3  Add room
 4  Set room Available / Maintenance
 5  Delete room
 6  Show customers
 7  Add customer
 8  Delete customer
 9  Book a room
10  Show bookings
11  Check-in guest
12  Take payment
13  Check-out guest
14  Cancel booking
15  Print invoice
16  Export CSV
 0  Exit
"""


def main():
    data = load_data()
    save_data(data)
    try:
        while True:
            print(MENU)
            choice = ask_text("Choose an option: ")

            if choice == "0":
                print("Goodbye!")
                break
            elif choice == "1":
                for label, value in dashboard(data).items():
                    print(f"  {label:<24}{value}")
            elif choice == "2":
                show_rooms(data)
            elif choice == "3":
                report(add_room(data, ask_text("Room number: "), ask_text("Type (Standard/Deluxe/Suite): "),
                                ask_number("Price per night (Rs): "), ask_number("Capacity: ")), data)
            elif choice == "4":
                show_rooms(data)
                report(set_room_status(data, ask_number("Room ID: "), ask_text("New status (Available/Maintenance): ")), data)
            elif choice == "5":
                show_rooms(data)
                report(delete_room(data, ask_number("Room ID to delete: ")), data)
            elif choice == "6":
                show_customers(data)
            elif choice == "7":
                report(add_customer(data, ask_text("Full name: "), ask_text("Email: "), ask_text("Phone: ")), data)
            elif choice == "8":
                show_customers(data)
                report(delete_customer(data, ask_number("Customer ID to delete: ")), data)
            elif choice == "9":
                show_customers(data)
                show_rooms(data)
                report(book_room(data, ask_number("Customer ID: "), ask_number("Room ID: "),
                                 ask_text("Check-in (YYYY-MM-DD): "), ask_text("Check-out (YYYY-MM-DD): "),
                                 ask_number("Number of guests: "), ask_number("Discount in Rs (0 for none): "),
                                 ask_number("Advance paid in Rs (0 for none): ")), data)
            elif choice == "10":
                show_bookings(data)
            elif choice == "11":
                show_bookings(data)
                report(check_in_guest(data, ask_number("Booking ID to check in: ")), data)
            elif choice == "12":
                show_bookings(data)
                report(take_payment(data, ask_number("Booking ID: "), ask_number("Amount received (Rs): ")), data)
            elif choice == "13":
                show_bookings(data)
                report(check_out_guest(data, ask_number("Booking ID to check out: ")), data)
            elif choice == "14":
                show_bookings(data)
                report(cancel_booking(data, ask_number("Booking ID to cancel: ")), data)
            elif choice == "15":
                show_bookings(data)
                ok, text = make_invoice(data, ask_number("Booking ID: "))
                print(text if ok else "ERROR: " + text)
            elif choice == "16":
                report(export_csv(data, ask_text("Export which? (rooms/customers/bookings): ").lower()), data)
            else:
                print("Please choose a number from the menu.")
    except (EOFError, KeyboardInterrupt):
        print("\nGoodbye!")


if __name__ == "__main__":
    main()
