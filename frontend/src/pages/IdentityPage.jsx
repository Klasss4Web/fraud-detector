import { useState } from 'react';
import { User } from 'lucide-react';
import Card from '../components/Card';
import Button from '../components/Button';
import { Input } from '../components/Input';
import AnalysisResult from '../components/AnalysisResult';
import { analyzeUserProfile } from '../services/api';
import useApi from '../hooks/useApi';
import './AnalysisPage.css';

const IdentityPage = () => {
  const { data: result, loading, error, execute } = useApi(analyzeUserProfile);
  
  const [formData, setFormData] = useState({
    user_id: '',
    email: '',
    phone: '',
    account_age_days: '',
    device_count: '1',
    login_frequency: '1',
    failed_login_attempts: '0',
    location_changes: '0',
  });

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const data = {
      ...formData,
      account_age_days: parseInt(formData.account_age_days) || 0,
      device_count: parseInt(formData.device_count) || 1,
      login_frequency: parseFloat(formData.login_frequency) || 1,
      failed_login_attempts: parseInt(formData.failed_login_attempts) || 0,
      location_changes: parseInt(formData.location_changes) || 0,
    };
    await execute(data, true);
  };

  return (
    <div className="analysis-page">
      <div className="page-header">
        <div className="page-header-icon page-header-icon-green">
          <User size={24} />
        </div>
        <div className="page-header-content">
          <h1 className="page-title">Identity Verification</h1>
          <p className="page-subtitle">
            Detect identity fraud including synthetic identity, account takeover, new account fraud, and identity theft indicators.
          </p>
        </div>
      </div>

      <div className="analysis-layout">
        <div className="analysis-form-container">
          <Card title="User Profile Details">
            <form onSubmit={handleSubmit} className="analysis-form">
              <div className="form-grid">
                <Input
                  label="User ID"
                  name="user_id"
                  value={formData.user_id}
                  onChange={handleChange}
                  placeholder="USER-12345"
                  required
                />
                <Input
                  label="Email"
                  name="email"
                  type="email"
                  value={formData.email}
                  onChange={handleChange}
                  placeholder="user@example.com"
                  required
                />
                <Input
                  label="Phone"
                  name="phone"
                  value={formData.phone}
                  onChange={handleChange}
                  placeholder="+1-555-123-4567"
                />
                <Input
                  label="Account Age (days)"
                  name="account_age_days"
                  type="number"
                  value={formData.account_age_days}
                  onChange={handleChange}
                  placeholder="365"
                  required
                />
                <Input
                  label="Device Count"
                  name="device_count"
                  type="number"
                  value={formData.device_count}
                  onChange={handleChange}
                  placeholder="1"
                />
                <Input
                  label="Login Frequency (per day)"
                  name="login_frequency"
                  type="number"
                  step="0.1"
                  value={formData.login_frequency}
                  onChange={handleChange}
                  placeholder="1.0"
                />
                <Input
                  label="Failed Login Attempts"
                  name="failed_login_attempts"
                  type="number"
                  value={formData.failed_login_attempts}
                  onChange={handleChange}
                  placeholder="0"
                />
                <Input
                  label="Location Changes"
                  name="location_changes"
                  type="number"
                  value={formData.location_changes}
                  onChange={handleChange}
                  placeholder="0"
                />
              </div>

              {error && (
                <div className="form-error">
                  {error}
                </div>
              )}

              <div className="form-actions">
                <Button type="submit" loading={loading}>
                  Verify Identity
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
                <User size={48} className="placeholder-icon" />
                <h3 className="placeholder-title">No Analysis Yet</h3>
                <p className="placeholder-text">
                  Fill in the user profile details and click "Verify Identity" to see the fraud analysis results.
                </p>
              </div>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
};

export default IdentityPage;
