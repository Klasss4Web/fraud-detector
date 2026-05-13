import { useState } from 'react';
import { FileText } from 'lucide-react';
import Card from '../components/Card';
import Button from '../components/Button';
import { Input, Select, TextArea } from '../components/Input';
import AnalysisResult from '../components/AnalysisResult';
import { analyzeInsuranceClaim } from '../services/api';
import useApi from '../hooks/useApi';
import './AnalysisPage.css';

const InsurancePage = () => {
  const { data: result, loading, error, execute } = useApi(analyzeInsuranceClaim);
  
  const [formData, setFormData] = useState({
    claim_id: '',
    claimant_id: '',
    claim_type: '',
    claim_amount: '',
    incident_date: '',
    filing_date: '',
    description: '',
    policy_id: '',
  });

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const data = {
      ...formData,
      claim_amount: parseFloat(formData.claim_amount) || 0,
    };
    await execute(data, true);
  };

  const claimTypes = [
    { value: 'auto', label: 'Auto Insurance' },
    { value: 'health', label: 'Health Insurance' },
    { value: 'property', label: 'Property Insurance' },
    { value: 'life', label: 'Life Insurance' },
    { value: 'liability', label: 'Liability Insurance' },
    { value: 'travel', label: 'Travel Insurance' },
    { value: 'other', label: 'Other' },
  ];

  return (
    <div className="analysis-page">
      <div className="page-header">
        <div className="page-header-icon page-header-icon-purple">
          <FileText size={24} />
        </div>
        <div className="page-header-content">
          <h1 className="page-title">Insurance Claim Analysis</h1>
          <p className="page-subtitle">
            Identify fraudulent insurance claims including staged incidents, exaggerated claims, serial claimants, and policy timing fraud.
          </p>
        </div>
      </div>

      <div className="analysis-layout">
        <div className="analysis-form-container">
          <Card title="Claim Details">
            <form onSubmit={handleSubmit} className="analysis-form">
              <div className="form-grid">
                <Input
                  label="Claim ID"
                  name="claim_id"
                  value={formData.claim_id}
                  onChange={handleChange}
                  placeholder="CLM-12345"
                  required
                />
                <Input
                  label="Claimant ID"
                  name="claimant_id"
                  value={formData.claimant_id}
                  onChange={handleChange}
                  placeholder="CLMT-12345"
                  required
                />
                <Select
                  label="Claim Type"
                  name="claim_type"
                  value={formData.claim_type}
                  onChange={handleChange}
                  options={claimTypes}
                  required
                />
                <Input
                  label="Claim Amount"
                  name="claim_amount"
                  type="number"
                  value={formData.claim_amount}
                  onChange={handleChange}
                  placeholder="5000.00"
                  required
                />
                <Input
                  label="Incident Date"
                  name="incident_date"
                  type="date"
                  value={formData.incident_date}
                  onChange={handleChange}
                  required
                />
                <Input
                  label="Filing Date"
                  name="filing_date"
                  type="date"
                  value={formData.filing_date}
                  onChange={handleChange}
                  required
                />
                <Input
                  label="Policy ID"
                  name="policy_id"
                  value={formData.policy_id}
                  onChange={handleChange}
                  placeholder="POL-12345"
                />
              </div>
              
              <TextArea
                label="Claim Description"
                name="description"
                value={formData.description}
                onChange={handleChange}
                placeholder="Describe the incident and claim details..."
                required
                rows={4}
              />

              {error && (
                <div className="form-error">
                  {error}
                </div>
              )}

              <div className="form-actions">
                <Button type="submit" loading={loading}>
                  Analyze Claim
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
                <FileText size={48} className="placeholder-icon" />
                <h3 className="placeholder-title">No Analysis Yet</h3>
                <p className="placeholder-text">
                  Fill in the claim details and click "Analyze Claim" to see the fraud analysis results.
                </p>
              </div>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
};

export default InsurancePage;
