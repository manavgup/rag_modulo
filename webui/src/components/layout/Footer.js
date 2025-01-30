import React from "react";
import { Link } from "react-router-dom";
import "./Footer.css";
import { Theme } from "@carbon/react";

const Footer = () => {
  return (
    <Theme theme="g100">
      <footer className="app-footer">
        <div className="footer-content">
          <div className="footer-section">
            <h4>IBM RAG Solution</h4>
            <p>&copy; {new Date().getFullYear()} IBM. All rights reserved.</p>
          </div>
          <div className="footer-section">
            <h4>Quick Links</h4>
            <ul>
              <li>
                <Link to="/">Dashboard</Link>
              </li>
              <li>
                <Link to="/search">Search</Link>
              </li>
              <li>
                <Link to="/collections">Collections</Link>
              </li>
            </ul>
          </div>
          <div className="footer-section">
            <h4>Support</h4>
            <ul>
              <li>
                <a href="#" onClick={(e) => e.preventDefault()}>
                  Help Center
                </a>
              </li>
              <li>
                <a href="#" onClick={(e) => e.preventDefault()}>
                  Documentation
                </a>
              </li>
              <li>
                <a href="#" onClick={(e) => e.preventDefault()}>
                  Contact Us
                </a>
              </li>
            </ul>
          </div>
        </div>
      </footer>
    </Theme>
  );
};

export default Footer;
