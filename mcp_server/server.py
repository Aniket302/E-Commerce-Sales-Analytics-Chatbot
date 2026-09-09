from fastmcp import FastMCP

from mcp_server.tools.orders import register_order_tools
from mcp_server.tools.categories import register_category_tools
from mcp_server.tools.sellers import register_seller_tools
from mcp_server.tools.reviews import register_review_tools
from mcp_server.tools.payments import register_payment_tools
from mcp_server.tools.delivery import register_delivery_tools

mcp = FastMCP("E-Commerce Analytics")

register_order_tools(mcp)
register_category_tools(mcp)
register_seller_tools(mcp)
register_review_tools(mcp)
register_payment_tools(mcp)
register_delivery_tools(mcp)

if __name__ == "__main__":
    mcp.run()