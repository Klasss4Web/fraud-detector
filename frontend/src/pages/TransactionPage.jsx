import { useState } from "react";
import { CreditCard } from "lucide-react";
import Card from "../components/Card";
import Button from "../components/Button";
import { Input, Select } from "../components/Input";
import AnalysisResult from "../components/AnalysisResult";
import { analyzeTransaction } from "../services/api";
import useApi from "../hooks/useApi";
import "./AnalysisPage.css";

const TransactionPage = () => {
  const { data: result, loading, error, execute } = useApi(analyzeTransaction);
  console.log({ loading });

  const [formData, setFormData] = useState({
    transaction_id: "",
    user_id: "",
    amount: "",
    currency: "USD",
    merchant_category: "",
    merchant_name: "",
    location: "",
    device_id: "",
    ip_address: "",
  });

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const data = {
      ...formData,
      amount: parseFloat(formData.amount) || 0,
    };
    await execute(data, true);
  };

  const merchantCategories = [
    { value: "retail", label: "Retail" },
    { value: "electronics", label: "Electronics" },
    { value: "grocery", label: "Grocery" },
    { value: "restaurant", label: "Restaurant" },
    { value: "travel", label: "Travel" },
    { value: "entertainment", label: "Entertainment" },
    { value: "gambling", label: "Gambling" },
    { value: "cryptocurrency", label: "Cryptocurrency" },
    { value: "money_transfer", label: "Money Transfer" },
    { value: "other", label: "Other" },
  ];

  const currencies = [
    { value: "USD", label: "USD - US Dollar" },
    { value: "EUR", label: "EUR - Euro" },
    { value: "GBP", label: "GBP - British Pound" },
    { value: "CAD", label: "CAD - Canadian Dollar" },
    { value: "AUD", label: "AUD - Australian Dollar" },
  ];

  return (
    <div className="analysis-page">
      <div className="page-header">
        <div className="page-header-icon page-header-icon-blue">
          <CreditCard size={24} />
        </div>
        <div className="page-header-content">
          <h1 className="page-title">Transaction Analysis</h1>
          <p className="page-subtitle">
            Analyze financial transactions for fraud detection including
            velocity attacks, amount anomalies, and geographic risks.
          </p>
        </div>
      </div>

      <div className="analysis-layout">
        <div className="analysis-form-container">
          <Card title="Transaction Details">
            <form onSubmit={handleSubmit} className="analysis-form">
              <div className="form-grid">
                <Input
                  label="Transaction ID"
                  name="transaction_id"
                  value={formData.transaction_id}
                  onChange={handleChange}
                  placeholder="TXN-12345"
                  required
                />
                <Input
                  label="User ID"
                  name="user_id"
                  value={formData.user_id}
                  onChange={handleChange}
                  placeholder="USER-12345"
                />
                <Input
                  label="Amount"
                  name="amount"
                  type="number"
                  value={formData.amount}
                  onChange={handleChange}
                  placeholder="100.00"
                  required
                />
                <Select
                  label="Currency"
                  name="currency"
                  value={formData.currency}
                  onChange={handleChange}
                  options={currencies}
                />
                <Select
                  label="Merchant Category"
                  name="merchant_category"
                  value={formData.merchant_category}
                  onChange={handleChange}
                  options={merchantCategories}
                  required
                />
                <Input
                  label="Merchant Name"
                  name="merchant_name"
                  value={formData.merchant_name}
                  onChange={handleChange}
                  placeholder="Store Name"
                  required
                />
                <Input
                  label="Location"
                  name="location"
                  value={formData.location}
                  onChange={handleChange}
                  placeholder="New York, US"
                  required
                />
                <Input
                  label="Device ID"
                  name="device_id"
                  value={formData.device_id}
                  onChange={handleChange}
                  placeholder="device-abc123"
                />
                <Input
                  label="IP Address"
                  name="ip_address"
                  value={formData.ip_address}
                  onChange={handleChange}
                  placeholder="192.168.1.1"
                />
              </div>

              {error && <div className="form-error">{error}</div>}

              <div className="form-actions">
                <Button type="submit" loading={loading}>
                  Analyze Transaction
                </Button>
              </div>
            </form>
          </Card>
        </div>

        <div className="analysis-result-container">
          {result && !loading && (
            <AnalysisResult result={result} loading={loading} />
          )}
          {!result && !loading && (
            <Card className="analysis-placeholder">
              <div className="placeholder-content">
                <CreditCard size={48} className="placeholder-icon" />
                <h3 className="placeholder-title">No Analysis Yet</h3>
                <p className="placeholder-text">
                  Fill in the transaction details and click "Analyze
                  Transaction" to see the fraud analysis results.
                </p>
              </div>
            </Card>
          )}

          {loading && (
            <div className="result-investigation-skeleton">
              <div className="skeleton-line" style={{ width: "80%" }}></div>
              <div className="skeleton-line" style={{ width: "95%" }}></div>
              <div className="skeleton-line" style={{ width: "90%" }}></div>
              <div className="skeleton-line" style={{ width: "85%" }}></div>
              <div className="skeleton-line" style={{ width: "80%" }}></div>
              <div className="skeleton-line" style={{ width: "70%" }}></div>
              <div className="skeleton-line" style={{ width: "60%" }}></div>
              <div className="skeleton-line" style={{ width: "55%" }}></div>
              <div className="skeleton-line" style={{ width: "50%" }}></div>
              <div className="skeleton-line" style={{ width: "45%" }}></div>
              <div className="skeleton-line" style={{ width: "40%" }}></div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default TransactionPage;
