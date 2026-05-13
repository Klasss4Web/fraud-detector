import { useState, useRef } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import {
  CreditCard,
  MapPin,
  User,
  Truck,
  Shield,
  ShieldCheck,
  ShieldAlert,
  ShieldX,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Clock,
  Info,
  ChevronLeft,
} from "lucide-react";
import Toast from "../components/Toast";
import { analyzeEcommerceOrder, analyzeTransaction } from "../services/api";
import "./StorePage.css";

const PAYMENT_METHODS = [
  { value: "credit_card", label: "Credit Card", icon: CreditCard },
  { value: "debit_card", label: "Debit Card", icon: CreditCard },
  { value: "paypal", label: "PayPal", icon: CreditCard },
  { value: "apple_pay", label: "Apple Pay", icon: CreditCard },
  { value: "google_pay", label: "Google Pay", icon: CreditCard },
  { value: "cryptocurrency", label: "Cryptocurrency", icon: CreditCard },
];

const FraudAnalysisResult = ({ result, orderStatus }) => {
  if (!result) return null;

  const riskLevel = result.risk_level || "low";
  const riskScore = result.risk_score || 0;
  const signals = result.signals || [];

  const getRiskIcon = () => {
    switch (riskLevel) {
      case "low":
        return <ShieldCheck size={24} />;
      case "medium":
        return <Shield size={24} />;
      case "high":
        return <ShieldAlert size={24} />;
      case "critical":
        return <ShieldX size={24} />;
      default:
        return <Shield size={24} />;
    }
  };

  const getRiskTitle = () => {
    switch (riskLevel) {
      case "low":
        return "Low Risk - Transaction Approved";
      case "medium":
        return "Medium Risk - Additional Verification May Be Required";
      case "high":
        return "High Risk - Manual Review Required";
      case "critical":
        return "Critical Risk - Transaction Blocked";
      default:
        return "Risk Assessment Complete";
    }
  };

  const getSignalWeight = (weight) => {
    if (weight >= 0.7) return "high";
    if (weight >= 0.4) return "medium";
    return "low";
  };

  return (
    <div className="fraud-analysis-container">
      <div className="fraud-analysis-card">
        <div className={`fraud-analysis-header risk-${riskLevel}`}>
          <div className="fraud-header-left">
            <div className="fraud-icon">{getRiskIcon()}</div>
            <div className="fraud-header-text">
              <h3>{getRiskTitle()}</h3>
              <p>AI-powered fraud detection analysis</p>
            </div>
          </div>
          <div className="risk-score-badge">{riskScore.toFixed(0)}</div>
        </div>

        <div className="fraud-analysis-body">
          {result.recommendation && (
            <div className="fraud-recommendation">
              <Info size={20} />
              <p>{result.recommendation}</p>
            </div>
          )}

          {signals.length > 0 && (
            <div className="fraud-signals">
              <h4>Detected Signals ({signals.length})</h4>
              <div className="signals-list">
                {signals.map((signal, idx) => {
                  const weightClass = getSignalWeight(signal.weight);
                  return (
                    <div key={idx} className={`signal-item weight-${weightClass}`}>
                      <div className="signal-icon">
                        <AlertTriangle size={16} />
                      </div>
                      <div className="signal-info">
                        <h5>{signal.name.replace(/_/g, " ").toUpperCase()}</h5>
                        <p>{signal.description}</p>
                      </div>
                      <span className="signal-weight">
                        {(signal.weight * 100).toFixed(0)}%
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          <div className={`order-status status-${orderStatus}`}>
            {orderStatus === "approved" && (
              <>
                <h4>
                  <CheckCircle size={20} /> Order Approved
                </h4>
                <p>Your order has been successfully processed and will be shipped soon.</p>
              </>
            )}
            {orderStatus === "review" && (
              <>
                <h4>
                  <Clock size={20} /> Under Review
                </h4>
                <p>Your order requires additional verification. We'll contact you shortly.</p>
              </>
            )}
            {orderStatus === "blocked" && (
              <>
                <h4>
                  <XCircle size={20} /> Order Blocked
                </h4>
                <p>This transaction has been blocked for security reasons. Please contact support.</p>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

const CheckoutPage = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const cart = location.state?.cart || [];
  
  const cartTotal = cart.reduce((sum, item) => sum + item.price * (item.quantity || 1), 0);
  const itemCount = cart.reduce((sum, item) => sum + (item.quantity || 1), 0);

  const [form, setForm] = useState({
    // Customer Info
    customer_id: `CUST-${Date.now().toString(36).toUpperCase()}`,
    email: "",
    phone: "",
    
    // Addresses
    shipping_address: "",
    shipping_city: "",
    shipping_country: "United States",
    billing_address: "",
    billing_city: "",
    billing_country: "United States",
    same_as_shipping: true,
    
    // Payment
    payment_method: "credit_card",
    card_number: "",
    card_expiry: "",
    card_cvv: "",
    
    // Options
    is_expedited: false,
  });

  const [result, setResult] = useState(null);
  const [orderStatus, setOrderStatus] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [toast, setToast] = useState(null);
  const toastTimeout = useRef();

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setForm((prev) => ({
      ...prev,
      [name]: type === "checkbox" ? checked : value,
    }));
  };

  const showToast = (message, type = "info", duration = 4000) => {
    setToast({ message, type });
    if (toastTimeout.current) clearTimeout(toastTimeout.current);
    toastTimeout.current = setTimeout(() => setToast(null), duration);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    setResult(null);
    setOrderStatus(null);

    try {
      // Build full addresses
      const shippingFull = `${form.shipping_address}, ${form.shipping_city}, ${form.shipping_country}`;
      const billingFull = form.same_as_shipping
        ? shippingFull
        : `${form.billing_address}, ${form.billing_city}, ${form.billing_country}`;

      // Prepare items
      const items = cart.map((item) => ({
        item_id: item.id,
        name: item.name,
        price: item.price,
        quantity: item.quantity || 1,
        category: item.category || "Electronics",
      }));

      // Check for high-risk items
      const HIGH_RISK_CATEGORIES = ["Electronics", "Gift Cards", "Jewelry", "Designer Items"];
      const high_risk_items = items.some((item) =>
        HIGH_RISK_CATEGORIES.includes(item.category)
      );

      // E-commerce order payload
      const orderPayload = {
        order_id: `ORD-${Date.now()}`,
        customer_id: form.customer_id,
        order_total: cartTotal,
        item_count: itemCount,
        shipping_address: shippingFull,
        billing_address: billingFull,
        payment_method: form.payment_method,
        express_shipping: form.is_expedited,
        is_new_customer: true,
        shipping_billing_match: form.same_as_shipping,
        previous_chargebacks: 0,
        high_risk_items,
        items,
      };

      // Also analyze as a transaction for additional fraud signals
      const transactionPayload = {
        transaction_id: `TXN-${Date.now()}`,
        amount: cartTotal,
        currency: "USD",
        merchant_category: "electronics",
        merchant_name: "TechShield Store",
        location: form.shipping_country,
        device_id: `device_${navigator.userAgent.slice(0, 10)}`,
        ip_address: "auto", // In real app, get from server
        timestamp: new Date().toISOString(),
        user_id: form.customer_id,
        // Add context for better fraud detection
        velocity_24h: 1,
        avg_amount_30d: cartTotal * 0.5, // Simulated
        is_international: form.shipping_country !== "United States",
        card_present: false,
      };

      // Run both analyses
      const [ecommerceResult, transactionResult] = await Promise.all([
        analyzeEcommerceOrder(orderPayload),
        analyzeTransaction(transactionPayload).catch(() => null),
      ]);

      // Use the higher risk score
      const finalResult = transactionResult && transactionResult.risk_score > ecommerceResult.risk_score
        ? transactionResult
        : ecommerceResult;

      setResult(finalResult);

      // Determine order status based on risk
      if (finalResult.risk_level === "low") {
        setOrderStatus("approved");
        showToast("Order approved! Your items will be shipped soon.", "success");
      } else if (finalResult.risk_level === "medium") {
        setOrderStatus("review");
        showToast("Order under review. Additional verification may be required.", "info");
      } else {
        setOrderStatus("blocked");
        showToast(`Order flagged as ${finalResult.risk_level.toUpperCase()} risk!`, "error");
      }
    } catch (err) {
      console.error("Checkout error:", err);
      setError("Failed to process order. Please try again.");
      showToast("Failed to process order. Please try again.", "error");
    }
    setLoading(false);
  };

  if (cart.length === 0) {
    return (
      <div className="checkout-container">
        <div className="checkout-content">
          <div className="checkout-header">
            <h1>Your cart is empty</h1>
            <p>Add some items to your cart before checking out.</p>
            <button
              className="submit-order-btn"
              style={{ maxWidth: 300, margin: "2rem auto" }}
              onClick={() => navigate("/store")}
            >
              <ChevronLeft size={18} />
              Back to Store
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <>
      {toast && (
        <Toast
          message={toast.message}
          type={toast.type}
          onClose={() => setToast(null)}
        />
      )}

      <div className="checkout-container">
        <div className="checkout-content">
          <div className="checkout-header">
            <h1>Secure Checkout</h1>
            <p>
              <Shield size={16} style={{ verticalAlign: "middle", marginRight: 6 }} />
              Protected by AI Fraud Detection
            </p>
          </div>

          <div className="checkout-grid">
            {/* Form Panel */}
            <form className="checkout-form-panel" onSubmit={handleSubmit}>
              {/* Customer Information */}
              <div className="form-section">
                <div className="form-section-header">
                  <User size={20} />
                  <h3>Customer Information</h3>
                </div>
                <div className="form-row">
                  <div className="form-group">
                    <label>Email Address</label>
                    <input
                      type="email"
                      name="email"
                      value={form.email}
                      onChange={handleChange}
                      placeholder="you@example.com"
                      required
                    />
                  </div>
                  <div className="form-group">
                    <label>Phone Number</label>
                    <input
                      type="tel"
                      name="phone"
                      value={form.phone}
                      onChange={handleChange}
                      placeholder="+1 (555) 000-0000"
                    />
                  </div>
                </div>
              </div>

              {/* Shipping Address */}
              <div className="form-section">
                <div className="form-section-header">
                  <Truck size={20} />
                  <h3>Shipping Address</h3>
                </div>
                <div className="form-row single">
                  <div className="form-group">
                    <label>Street Address</label>
                    <input
                      type="text"
                      name="shipping_address"
                      value={form.shipping_address}
                      onChange={handleChange}
                      placeholder="123 Main Street, Apt 4B"
                      required
                    />
                  </div>
                </div>
                <div className="form-row">
                  <div className="form-group">
                    <label>City</label>
                    <input
                      type="text"
                      name="shipping_city"
                      value={form.shipping_city}
                      onChange={handleChange}
                      placeholder="New York"
                      required
                    />
                  </div>
                  <div className="form-group">
                    <label>Country</label>
                    <select
                      name="shipping_country"
                      value={form.shipping_country}
                      onChange={handleChange}
                    >
                      <option>United States</option>
                      <option>Canada</option>
                      <option>United Kingdom</option>
                      <option>Germany</option>
                      <option>France</option>
                      <option>Nigeria</option>
                      <option>Russia</option>
                      <option>China</option>
                      <option>India</option>
                    </select>
                  </div>
                </div>
                <div className="form-row single">
                  <label className="checkbox-group">
                    <input
                      type="checkbox"
                      name="same_as_shipping"
                      checked={form.same_as_shipping}
                      onChange={handleChange}
                    />
                    <div className="checkbox-label">
                      <span>Billing address same as shipping</span>
                      <span>Use my shipping address for billing</span>
                    </div>
                  </label>
                </div>
              </div>

              {/* Billing Address (if different) */}
              {!form.same_as_shipping && (
                <div className="form-section">
                  <div className="form-section-header">
                    <MapPin size={20} />
                    <h3>Billing Address</h3>
                  </div>
                  <div className="form-row single">
                    <div className="form-group">
                      <label>Street Address</label>
                      <input
                        type="text"
                        name="billing_address"
                        value={form.billing_address}
                        onChange={handleChange}
                        placeholder="456 Other Street"
                        required
                      />
                    </div>
                  </div>
                  <div className="form-row">
                    <div className="form-group">
                      <label>City</label>
                      <input
                        type="text"
                        name="billing_city"
                        value={form.billing_city}
                        onChange={handleChange}
                        placeholder="Los Angeles"
                        required
                      />
                    </div>
                    <div className="form-group">
                      <label>Country</label>
                      <select
                        name="billing_country"
                        value={form.billing_country}
                        onChange={handleChange}
                      >
                        <option>United States</option>
                        <option>Canada</option>
                        <option>United Kingdom</option>
                        <option>Germany</option>
                        <option>France</option>
                        <option>Nigeria</option>
                        <option>Russia</option>
                        <option>China</option>
                        <option>India</option>
                      </select>
                    </div>
                  </div>
                </div>
              )}

              {/* Payment */}
              <div className="form-section">
                <div className="form-section-header">
                  <CreditCard size={20} />
                  <h3>Payment Method</h3>
                </div>
                <div className="form-row single">
                  <div className="form-group">
                    <label>Payment Type</label>
                    <select
                      name="payment_method"
                      value={form.payment_method}
                      onChange={handleChange}
                    >
                      {PAYMENT_METHODS.map((method) => (
                        <option key={method.value} value={method.value}>
                          {method.label}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
                <div className="form-row single">
                  <div className="form-group">
                    <label>Card Number</label>
                    <input
                      type="text"
                      name="card_number"
                      value={form.card_number}
                      onChange={handleChange}
                      placeholder="4242 4242 4242 4242"
                      maxLength={19}
                    />
                  </div>
                </div>
                <div className="form-row">
                  <div className="form-group">
                    <label>Expiry Date</label>
                    <input
                      type="text"
                      name="card_expiry"
                      value={form.card_expiry}
                      onChange={handleChange}
                      placeholder="MM/YY"
                      maxLength={5}
                    />
                  </div>
                  <div className="form-group">
                    <label>CVV</label>
                    <input
                      type="text"
                      name="card_cvv"
                      value={form.card_cvv}
                      onChange={handleChange}
                      placeholder="123"
                      maxLength={4}
                    />
                  </div>
                </div>
              </div>

              {/* Shipping Options */}
              <div className="form-section">
                <div className="form-section-header">
                  <Truck size={20} />
                  <h3>Shipping Options</h3>
                </div>
                <div className="form-row single">
                  <label className="checkbox-group">
                    <input
                      type="checkbox"
                      name="is_expedited"
                      checked={form.is_expedited}
                      onChange={handleChange}
                    />
                    <div className="checkbox-label">
                      <span>Express Shipping (+$25)</span>
                      <span>Get your order in 1-2 business days</span>
                    </div>
                  </label>
                </div>
              </div>

              {error && (
                <div className="form-section" style={{ color: "#ef4444", textAlign: "center" }}>
                  {error}
                </div>
              )}
            </form>

            {/* Right Column - Order Summary & Fraud Analysis */}
            <div className="checkout-right-column">
              <div className="order-summary-panel">
                <div className="summary-header">
                  <h3>Order Summary</h3>
                </div>

                <ul className="cart-items">
                  {cart.map((item, idx) => (
                    <li key={idx} className="cart-item">
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
                          ${(item.price * (item.quantity || 1)).toLocaleString()}
                        </span>
                      </div>
                      <span className="cart-item-qty">Qty: {item.quantity || 1}</span>
                    </li>
                  ))}
                </ul>

                <div className="summary-totals">
                  <div className="summary-row">
                    <span>Subtotal</span>
                    <span>${cartTotal.toLocaleString()}</span>
                  </div>
                  <div className="summary-row">
                    <span>Shipping</span>
                    <span style={{ color: form.is_expedited ? "#1e293b" : "#10b981" }}>
                      {form.is_expedited ? "$25" : "FREE"}
                    </span>
                  </div>
                  <div className="summary-row total">
                    <span>Total</span>
                    <span>${(cartTotal + (form.is_expedited ? 25 : 0)).toLocaleString()}</span>
                  </div>
                </div>

                <button
                  type="submit"
                  className="submit-order-btn"
                  onClick={handleSubmit}
                  disabled={loading}
                >
                  {loading ? (
                    <>
                      <span className="btn-spinner"></span>
                      Processing...
                    </>
                  ) : (
                    <>
                      <Shield size={18} />
                      Place Secure Order
                    </>
                  )}
                </button>

                <div className="security-badge" style={{ margin: "0 1.5rem 1.5rem" }}>
                  <ShieldCheck size={16} />
                  <span>256-bit SSL Encrypted</span>
                </div>
              </div>

              {/* Fraud Analysis Result */}
              {result && <FraudAnalysisResult result={result} orderStatus={orderStatus} />}
            </div>
          </div>
        </div>
      </div>
    </>
  );
};

export default CheckoutPage;
