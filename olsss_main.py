"""
Online Lunch Sale & Tally System (OLSSS)
Separated from the main timetable generator for better organization
"""

from fastapi import FastAPI, HTTPException, Request, Response, Cookie
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from datetime import datetime
import json
import asyncio
from typing import List, Dict, Any, Optional


# Global storage for lunch orders (in production, use database)
lunch_orders = {}  # order_id -> order_data
order_counter = 0
admin_password = "admin123"  # Simple admin password

# SSE (Server-Sent Events) for real-time updates
connected_clients = set()


async def notify_clients(event_type: str, data: dict):
    """Send real-time updates to all connected clients"""
    if not connected_clients:
        return
    
    message = f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
    
    # Send to all connected clients
    disconnected_clients = set()
    for client_queue in connected_clients:
        try:
            await client_queue.put(message)
        except:
            # Client disconnected
            disconnected_clients.add(client_queue)
    
    # Remove disconnected clients
    for client in disconnected_clients:
        connected_clients.discard(client)


class LunchOrder:
    def __init__(self, order_id: int, name: str, order_description: str, price: float, session_id: str = None):
        self.order_id = order_id
        self.name = name
        self.order_description = order_description
        self.price = price
        self.paid = False
        self.timestamp = datetime.now()
        self.session_id = session_id  # Track who created this order
    
    def to_dict(self):
        return {
            "order_id": self.order_id,
            "name": self.name,
            "order_description": self.order_description,
            "price": self.price,
            "paid": self.paid,
            "timestamp": self.timestamp.isoformat(),
            "session_id": self.session_id
        }


def get_next_order_id():
    global order_counter
    order_counter += 1
    return order_counter


def add_lunch_order(name: str, order_description: str, price: float, session_id: str = None):
    """Add a new lunch order"""
    order_id = get_next_order_id()
    order = LunchOrder(order_id, name, order_description, price, session_id)
    lunch_orders[order_id] = order
    return order


def get_all_lunch_orders():
    """Get all lunch orders"""
    return [order.to_dict() for order in sorted(lunch_orders.values(), key=lambda o: o.timestamp, reverse=True)]


def mark_order_paid(order_id: int, paid: bool = True):
    """Mark an order as paid or unpaid"""
    if order_id in lunch_orders:
        lunch_orders[order_id].paid = paid
        return True
    return False


def get_order_statistics():
    """Get order statistics"""
    total_orders = len(lunch_orders)
    paid_orders = sum(1 for order in lunch_orders.values() if order.paid)
    unpaid_orders = total_orders - paid_orders
    total_amount = sum(order.price for order in lunch_orders.values())
    paid_amount = sum(order.price for order in lunch_orders.values() if order.paid)
    unpaid_amount = total_amount - paid_amount
    
    return {
        "total_orders": total_orders,
        "paid_orders": paid_orders,
        "unpaid_orders": unpaid_orders,
        "total_amount": round(total_amount, 2),
        "paid_amount": round(paid_amount, 2),
        "unpaid_amount": round(unpaid_amount, 2)
    }


def delete_lunch_order(order_id: int):
    """Delete a lunch order"""
    if order_id in lunch_orders:
        del lunch_orders[order_id]
        return True
    return False


def get_session_id_olsss(session_id: str = None):
    """Helper function to get session ID for OLSSS"""
    import uuid
    if session_id is None:
        session_id = str(uuid.uuid4())
    return session_id


# OLSSS Route handlers - these will be registered in the main app
async def olsss_page(request: Request, templates):
    """Main lunch orders page"""
    return templates.TemplateResponse("lunch_orders.html", {"request": request})


async def add_order(request: Request, session_id: str = None):
    """Add a new lunch order"""
    try:
        data = await request.json()
        name = data.get("name", "").strip()
        order_description = data.get("order_description", "").strip()
        price = float(data.get("price", 0))
        
        if not name:
            raise HTTPException(status_code=400, detail="Name is required")
        if not order_description:
            raise HTTPException(status_code=400, detail="Order description is required")
        if price <= 0:
            raise HTTPException(status_code=400, detail="Price must be greater than 0")
        
        order = add_lunch_order(name, order_description, price, session_id)
        
        # Notify all connected clients
        await notify_clients("order_added", {
            "order": order.to_dict(),
            "statistics": get_order_statistics()
        })
        
        return {
            "success": True,
            "message": "Order added successfully",
            "order": order.to_dict()
        }
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid price format")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def update_order(request: Request, session_id: str = None):
    """Update an existing lunch order"""
    try:
        data = await request.json()
        order_id = int(data.get("order_id"))
        name = data.get("name", "").strip()
        order_description = data.get("order_description", "").strip()
        price = float(data.get("price", 0))
        password = data.get("password", "")
        
        if not name:
            raise HTTPException(status_code=400, detail="Name is required")
        if not order_description:
            raise HTTPException(status_code=400, detail="Order description is required")
        if price <= 0:
            raise HTTPException(status_code=400, detail="Price must be greater than 0")
        
        if order_id not in lunch_orders:
            raise HTTPException(status_code=404, detail="Order not found")

        order = lunch_orders[order_id]
        is_admin = password == admin_password
        is_owner = order.session_id == session_id

        if not is_admin and not is_owner:
            raise HTTPException(status_code=403, detail="You do not have permission to edit this order")

        # Update the order details
        order.name = name
        order.order_description = order_description
        order.price = price

        # Notify all connected clients
        await notify_clients("order_updated", {
            "order": order.to_dict(),
            "statistics": get_order_statistics()
        })
        
        return {
            "success": True,
            "message": "Order updated successfully",
            "order": order.to_dict()
        }
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid price format")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def get_orders(session_id: str = None):
    """Get all lunch orders and indicate which are owned by the user"""
    orders_data = []
    for order in sorted(lunch_orders.values(), key=lambda o: o.timestamp, reverse=True):
        order_dict = order.to_dict()
        order_dict["is_owner"] = (order.session_id == session_id)
        orders_data.append(order_dict)

    return {
        "success": True,
        "orders": orders_data,
        "statistics": get_order_statistics()
    }


async def mark_paid(request: Request):
    """Mark an order as paid/unpaid (Admin only)"""
    try:
        data = await request.json()
        order_id = int(data.get("order_id"))
        paid = data.get("paid", True)
        password = data.get("password", "")
        
        if password != admin_password:
            raise HTTPException(status_code=401, detail="Invalid admin password")
        
        success = mark_order_paid(order_id, paid)
        if success:
            order_data = lunch_orders[order_id].to_dict() if order_id in lunch_orders else {}
            await notify_clients("order_updated", {
                "order": order_data,
                "statistics": get_order_statistics()
            })
            return {
                "success": True,
                "message": f"Order {'marked as paid' if paid else 'marked as unpaid'}"
            }
        else:
            raise HTTPException(status_code=404, detail="Order not found")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid order ID")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def delete_order(request: Request, session_id: str = None):
    """Delete an order (Admin or Owner)"""
    try:
        data = await request.json()
        order_id = int(data.get("order_id"))
        password = data.get("password", "")
        
        if order_id not in lunch_orders:
            raise HTTPException(status_code=404, detail="Order not found")
        
        order = lunch_orders[order_id]
        is_admin = password == admin_password
        is_owner = order.session_id == session_id
        
        if not is_admin and not is_owner:
            raise HTTPException(status_code=403, detail="You do not have permission to delete this order")
        
        success = delete_lunch_order(order_id)
        if success:
            await notify_clients("order_deleted", {
                "order_id": order_id,
                "statistics": get_order_statistics()
            })
            return {
                "success": True,
                "message": "Order deleted successfully"
            }
        else:
            raise HTTPException(status_code=404, detail="Order not found")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid order ID")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def admin_login(request: Request):
    """Simple admin authentication"""
    try:
        data = await request.json()
        password = data.get("password", "")
        
        if password == admin_password:
            return {
                "success": True,
                "message": "Admin authenticated successfully"
            }
        else:
            raise HTTPException(status_code=401, detail="Invalid admin password")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def get_statistics():
    """Get order statistics"""
    return {
        "success": True,
        "statistics": get_order_statistics()
    }


async def stream_events(session_id: str = None):
    """Server-Sent Events endpoint for real-time updates"""
    async def event_generator():
        # Create a queue for this client
        client_queue = asyncio.Queue()
        connected_clients.add(client_queue)
        
        try:
            # Send initial data with ownership info
            orders_data = []
            for order in sorted(lunch_orders.values(), key=lambda o: o.timestamp, reverse=True):
                order_dict = order.to_dict()
                order_dict["is_owner"] = (order.session_id == session_id)
                orders_data.append(order_dict)

            initial_data = {
                "orders": orders_data,
                "statistics": get_order_statistics()
            }
            yield f"event: initial_data\ndata: {json.dumps(initial_data)}\n\n"
            
            # Keep connection alive and send updates
            while True:
                try:
                    # Wait for new events
                    message = await asyncio.wait_for(client_queue.get(), timeout=30.0)
                    yield message
                except asyncio.TimeoutError:
                    # Send heartbeat to keep connection alive
                    yield f"event: heartbeat\ndata: {json.dumps({'timestamp': datetime.now().isoformat()})}\n\n"
                    
        except Exception as e:
            print(f"SSE client disconnected: {e}")
        finally:
            # Clean up when client disconnects
            connected_clients.discard(client_queue)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )


def register_olsss_routes(app: FastAPI, templates):
    """Register all OLSSS routes with the main FastAPI app"""
    
    @app.get("/OLSSS", response_class=HTMLResponse)
    async def olsss_page_route(request: Request):
        return await olsss_page(request, templates)

    @app.post("/OLSSS/add-order")
    async def add_order_route(request: Request, response: Response, session_id: str = Cookie(None)):
        import uuid
        
        def get_session_id_local(session_id: str = None):
            if session_id is None:
                session_id = str(uuid.uuid4())
            return session_id
        
        SESSION_COOKIE = "session_id"
        session_id = get_session_id_local(session_id)
        response.set_cookie(key=SESSION_COOKIE, value=session_id, httponly=True)
        return await add_order(request, session_id)

    @app.post("/OLSSS/update-order")
    async def update_order_route(request: Request, response: Response, session_id: str = Cookie(None)):
        import uuid
        
        def get_session_id_local(session_id: str = None):
            if session_id is None:
                session_id = str(uuid.uuid4())
            return session_id
        
        SESSION_COOKIE = "session_id"
        session_id = get_session_id_local(session_id)
        response.set_cookie(key=SESSION_COOKIE, value=session_id, httponly=True)
        return await update_order(request, session_id)

    @app.get("/OLSSS/orders")
    async def get_orders_route(response: Response, session_id: str = Cookie(None)):
        import uuid
        
        def get_session_id_local(session_id: str = None):
            if session_id is None:
                session_id = str(uuid.uuid4())
            return session_id
        
        SESSION_COOKIE = "session_id"
        session_id = get_session_id_local(session_id)
        response.set_cookie(key=SESSION_COOKIE, value=session_id, httponly=True)
        return await get_orders(session_id)

    @app.post("/OLSSS/mark-paid")
    async def mark_paid_route(request: Request):
        return await mark_paid(request)

    @app.post("/OLSSS/delete-order")
    async def delete_order_route(request: Request, response: Response, session_id: str = Cookie(None)):
        import uuid
        
        def get_session_id_local(session_id: str = None):
            if session_id is None:
                session_id = str(uuid.uuid4())
            return session_id
        
        SESSION_COOKIE = "session_id"
        session_id = get_session_id_local(session_id)
        response.set_cookie(key=SESSION_COOKIE, value=session_id, httponly=True)
        return await delete_order(request, session_id)

    @app.post("/OLSSS/admin-login")
    async def admin_login_route(request: Request):
        return await admin_login(request)

    @app.get("/OLSSS/statistics")
    async def get_statistics_route():
        return await get_statistics()

    @app.get("/OLSSS/events")
    async def stream_events_route(response: Response, session_id: str = Cookie(None)):
        import uuid
        
        def get_session_id_local(session_id: str = None):
            if session_id is None:
                session_id = str(uuid.uuid4())
            return session_id
        
        SESSION_COOKIE = "session_id"
        session_id = get_session_id_local(session_id)
        response.set_cookie(key=SESSION_COOKIE, value=session_id, httponly=True)
        return await stream_events(session_id)
