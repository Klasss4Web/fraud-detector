import { useState } from 'react';
import { ShoppingCart } from 'lucide-react';
import Card from '../components/Card';
import Button from '../components/Button';
import { Input, Select } from '../components/Input';
import AnalysisResult from '../components/AnalysisResult';
import { analyzeEcommerceOrder } from '../services/api';
import useApi from '../hooks/useApi';
import './AnalysisPage.css';

const EcommercePage = () => {
  const { data: result, loading, error, execute } = useApi(analyzeEcommerceOrder);
  
  const [formData, setFormData] = useState({
    order_id: '',
    customer_id: '',
    order_total: '',
    item_count: '1',
    shipping_address: '',
    billing_address: '',
    payment_method: '',
    is_expedited: 'false',
  });

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const data = {
      ...formData,
      order_total: parseFloat(formData.order_total) || 0,
      item_count: parseInt(formData.item_count) || 1,
      is_expedited: formData.is_expedited === 'true',
    };
    await execute(data, true);
  };

  const paymentMethods = [
    { value: 'credit_card', label: 'Credit Card' },
    { value: 'debit_card', label: 'Debit Card' },
    { value: 'paypal', label: 'PayPal' },
    { value: 'apple_pay', label: 'Apple Pay' },
    { value: 'google_pay', label: 'Google Pay' },
    { value: 'prepaid_card', label: 'Prepaid Card' },
    { value: 'cryptocurrency', label: 'Cryptocurrency' },
    { value: 'bank_transfer', label: 'Bank Transfer' },
  ];

  const expeditedOptions = [
    { value: 'false', label: 'Standard Shipping' },
    { value: 'true', label: 'Expedited Shipping' },
  ];

  return (
    <div className="analysis-page">
      <div className="page-header">
        <div className="page-header-icon page-header-icon-orange">
          <ShoppingCart size={24} />
        </div>
        <div className="page-header-content">
          <h1 className="page-title">E-Commerce Order Analysis</h1>
          <p className="page-subtitle">
            Analyze e-commerce orders for reseller fraud, stolen cards, friendly fraud, and address mismatches.
          </p>
        </div>
      </div>

      <div className="analysis-layout">
        <div className="analysis-form-container">
          <Card title="Order Details">
            <form onSubmit={handleSubmit} className="analysis-form">
              <div className="form-grid">
                <Input
                  label="Order ID"
                  name="order_id"
                  value={formData.order_id}
                  onChange={handleChange}
                  placeholder="ORD-12345"
                  required
                />
                <Input
                  label="Customer ID"
                  name="customer_id"
                  value={formData.customer_id}
                  onChange={handleChange}
                  placeholder="CUST-12345"
                  required
                />
                <Input
                  label="Order Total"
                  name="order_total"
                  type="number"
                  value={formData.order_total}
                  onChange={handleChange}
                  placeholder="150.00"
                  required
                />
                <Input
                  label="Item Count"
                  name="item_count"
                  type="number"
                  value={formData.item_count}
                  onChange={handleChange}
                  placeholder="1"
                  required
                />
                <Select
                  label="Payment Method"
                  name="payment_method"
                  value={formData.payment_method}
                  onChange={handleChange}
                  options={paymentMethods}
                  required
                />
                <Select
                  label="Shipping Type"
                  name="is_expedited"
                  value={formData.is_expedited}
                  onChange={handleChange}
                  options={expeditedOptions}
                />
              </div>
              
              <Input
                label="Shipping Address"
                name="shipping_address"
                value={formData.shipping_address}
                onChange={handleChange}
                placeholder="123 Main St, New York, NY 10001"
                required
              />
              
              <Input
                label="Billing Address"
                name="billing_address"
                value={formData.billing_address}
                onChange={handleChange}
                placeholder="123 Main St, New York, NY 10001"
                required
              />

              {error && (
                <div className="form-error">
                  {error}
                </div>
              )}

              <div className="form-actions">
                <Button type="submit" loading={loading}>
                  Analyze Order
                </Button>
              </div>
            </form>
          </Card>
        </div>

        <div className="analysis-result-container">
          {result ? (
            <AnalysisResult result={result} />
          ) : (
            <Card className="analysis-placeholder">
              <div className="placeholder-content">
                <ShoppingCart size={48} className="placeholder-icon" />
                <h3 className="placeholder-title">No Analysis Yet</h3>
                <p className="placeholder-text">
                  Fill in the order details and click "Analyze Order" to see the fraud analysis results.
                </p>
              </div>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
};

export default EcommercePage;
