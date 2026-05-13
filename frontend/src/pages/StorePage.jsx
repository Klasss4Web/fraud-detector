import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ShoppingCart, Plus, Minus, Trash2, ShoppingBag, Shield, CreditCard } from "lucide-react";
import "./StorePage.css";

const PRODUCTS = [
  {
    id: 1,
    name: "MacBook Pro 16\"",
    price: 2499,
    category: "Electronics",
    description: "Apple M3 Pro chip, 18GB RAM, 512GB SSD",
    image: "https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=400&h=300&fit=crop",
    badge: "Popular",
  },
  {
    id: 2,
    name: "iPhone 15 Pro",
    price: 1199,
    category: "Electronics",
    description: "6.1\" Super Retina XDR, A17 Pro chip",
    image: "https://images.unsplash.com/photo-1592750475338-74b7b21085ab?w=400&h=300&fit=crop",
    badge: "New",
  },
  {
    id: 3,
    name: "Sony WH-1000XM5",
    price: 349,
    category: "Electronics",
    description: "Industry-leading noise cancellation",
    image: "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=400&h=300&fit=crop",
    badge: null,
  },
  {
    id: 4,
    name: "Apple Watch Ultra 2",
    price: 799,
    category: "Electronics",
    description: "49mm titanium case, GPS + Cellular",
    image: "https://images.unsplash.com/photo-1434493789847-2f02dc6ca35d?w=400&h=300&fit=crop",
    badge: "Hot",
  },
  {
    id: 5,
    name: "iPad Pro 12.9\"",
    price: 1099,
    category: "Electronics",
    description: "M2 chip, Liquid Retina XDR display",
    image: "https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?w=400&h=300&fit=crop",
    badge: null,
  },
  {
    id: 6,
    name: "AirPods Pro 2",
    price: 249,
    category: "Electronics",
    description: "Active Noise Cancellation, USB-C",
    image: "https://images.unsplash.com/photo-1606220588913-b3aacb4d2f46?w=400&h=300&fit=crop",
    badge: "Best Seller",
  },
];

const StorePage = () => {
  const [cart, setCart] = useState([]);
  const navigate = useNavigate();

  const addToCart = (product) => {
    const existingItem = cart.find((item) => item.id === product.id);
    if (existingItem) {
      setCart(
        cart.map((item) =>
          item.id === product.id
            ? { ...item, quantity: item.quantity + 1 }
            : item
        )
      );
    } else {
      setCart([...cart, { ...product, quantity: 1 }]);
    }
  };

  const updateQuantity = (id, delta) => {
    setCart(
      cart
        .map((item) =>
          item.id === id
            ? { ...item, quantity: Math.max(0, item.quantity + delta) }
            : item
        )
        .filter((item) => item.quantity > 0)
    );
  };

  const removeFromCart = (id) => {
    setCart(cart.filter((item) => item.id !== id));
  };

  const cartTotal = cart.reduce((sum, item) => sum + item.price * item.quantity, 0);
  const cartItemCount = cart.reduce((sum, item) => sum + item.quantity, 0);

  const handleCheckout = () => {
    navigate("/checkout", { state: { cart } });
  };

  return (
    <div className="store-container">
      {/* Header */}
      <header className="store-header">
        <div className="store-header-content">
          <div className="store-brand">
            <ShoppingBag size={32} className="store-logo" />
            <div>
              <h1>TechShield Store</h1>
              <p className="store-tagline">
                <Shield size={14} /> Protected by AI Fraud Detection
              </p>
            </div>
          </div>
          <div className="store-cart-indicator" onClick={() => document.getElementById('cart-section').scrollIntoView({ behavior: 'smooth' })}>
            <ShoppingCart size={24} />
            {cartItemCount > 0 && (
              <span className="cart-badge">{cartItemCount}</span>
            )}
          </div>
        </div>
      </header>

      <div className="store-layout">
        {/* Products Grid */}
        <main className="products-section">
          <div className="section-header">
            <h2>Featured Products</h2>
            <p>Premium electronics with secure checkout</p>
          </div>
          <div className="products-grid">
            {PRODUCTS.map((product) => (
              <article key={product.id} className="product-card">
                {product.badge && (
                  <span className={`product-badge badge-${product.badge.toLowerCase().replace(' ', '-')}`}>
                    {product.badge}
                  </span>
                )}
                <div className="product-image-container">
                  <img
                    src={product.image}
                    alt={product.name}
                    className="product-image"
                    onError={(e) => {
                      e.target.src = "https://via.placeholder.com/400x300?text=Product";
                    }}
                  />
                </div>
                <div className="product-info">
                  <span className="product-category">{product.category}</span>
                  <h3 className="product-name">{product.name}</h3>
                  <p className="product-description">{product.description}</p>
                  <div className="product-footer">
                    <span className="product-price">${product.price.toLocaleString()}</span>
                    <button
                      className="add-to-cart-btn"
                      onClick={() => addToCart(product)}
                    >
                      <Plus size={18} />
                      Add
                    </button>
                  </div>
                </div>
              </article>
            ))}
          </div>
        </main>

        {/* Cart Sidebar */}
        <aside className="cart-section" id="cart-section">
          <div className="cart-header">
            <ShoppingCart size={20} />
            <h2>Shopping Cart</h2>
            <span className="cart-count">{cartItemCount} items</span>
          </div>

          {cart.length === 0 ? (
            <div className="cart-empty">
              <ShoppingBag size={48} strokeWidth={1} />
              <p>Your cart is empty</p>
              <span>Add some products to get started</span>
            </div>
          ) : (
            <>
              <ul className="cart-items">
                {cart.map((item) => (
                  <li key={item.id} className="cart-item">
                    <img
                      src={item.image}
                      alt={item.name}
                      className="cart-item-image"
                      onError={(e) => {
                        e.target.src = "https://via.placeholder.com/60x60?text=Item";
                      }}
                    />
                    <div className="cart-item-details">
                      <h4>{item.name}</h4>
                      <span className="cart-item-price">
                        ${(item.price * item.quantity).toLocaleString()}
                      </span>
                    </div>
                    <div className="cart-item-actions">
                      <div className="quantity-controls">
                        <button
                          onClick={() => updateQuantity(item.id, -1)}
                          className="qty-btn"
                        >
                          <Minus size={14} />
                        </button>
                        <span className="qty-value">{item.quantity}</span>
                        <button
                          onClick={() => updateQuantity(item.id, 1)}
                          className="qty-btn"
                        >
                          <Plus size={14} />
                        </button>
                      </div>
                      <button
                        onClick={() => removeFromCart(item.id)}
                        className="remove-btn"
                      >
                        <Trash2 size={16} />
                      </button>
                    </div>
                  </li>
                ))}
              </ul>

              <div className="cart-summary">
                <div className="cart-subtotal">
                  <span>Subtotal</span>
                  <span>${cartTotal.toLocaleString()}</span>
                </div>
                <div className="cart-shipping">
                  <span>Shipping</span>
                  <span className="free-shipping">FREE</span>
                </div>
                <div className="cart-total">
                  <span>Total</span>
                  <span>${cartTotal.toLocaleString()}</span>
                </div>

                <button
                  className="checkout-btn"
                  onClick={handleCheckout}
                  disabled={cart.length === 0}
                >
                  <CreditCard size={18} />
                  Proceed to Checkout
                </button>

                <div className="security-badge">
                  <Shield size={16} />
                  <span>Secured by AI Fraud Detection</span>
                </div>
              </div>
            </>
          )}
        </aside>
      </div>
    </div>
  );
};

export default StorePage;
