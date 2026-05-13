import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import Button from '../components/Button';
import { Input } from '../components/Input';
import Card from '../components/Card';
import './LoginPage.css';

const LoginPage = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { login, error, clearError } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    
    const result = await login(email, password);
    
    if (result.success) {
      navigate('/');
    }
    
    setIsSubmitting(false);
  };

  return (
    <div className="login-page">
      <div className="login-container">
        <div className="login-header">
          <div className="login-logo">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
              <path d="M9 12l2 2 4-4" />
            </svg>
          </div>
          <h1>Fraud Detection System</h1>
          <p>Sign in to your account</p>
        </div>

        <Card>
          <form onSubmit={handleSubmit} className="login-form">
            {error && (
              <div className="login-error">
                <span>{error}</span>
                <button type="button" onClick={clearError} className="error-close">×</button>
              </div>
            )}

            <Input
              label="Email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              required
            />

            <Input
              label="Password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              required
            />

            <Button
              type="submit"
              variant="primary"
              fullWidth
              loading={isSubmitting}
            >
              Sign In
            </Button>

            <div className="login-footer">
              <p>
                Don't have an account?{' '}
                <Link to="/register">Create one</Link>
              </p>
            </div>
          </form>
        </Card>

        <div className="login-demo-note">
          <p>
            <strong>Demo Mode:</strong> Authentication is optional. 
            You can <Link to="/">continue without logging in</Link>.
          </p>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
