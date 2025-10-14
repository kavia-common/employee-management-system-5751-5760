/// <reference types="cypress" />
/**
 * Example Cypress E2E test for login behavior.
 * This spec assumes the frontend is served at process.env.CYPRESS_BASE_URL
 * and the backend at REACT_APP_API_BASE_URL configured in the frontend.
 *
 * It verifies:
 *  - User can log in with valid credentials
 *  - Response contains access_token
 *  - Token is stored (e.g., localStorage key 'auth_token')
 *  - User is redirected to /dashboard
 *
 * Prerequisites:
 *  - Backend running and accessible
 *  - A user exists in the backend (or sign up in the test via API)
 */

describe("Login flow", () => {
  const email = `user_${Date.now()}@example.com`;
  const password = "StrongPass123";

  function signupViaApi() {
    const api = Cypress.env("REACT_APP_API_BASE_URL") || "http://localhost:3002";
    return cy.request({
      method: "POST",
      url: `${api}/auth/signup`,
      body: { email, password },
      failOnStatusCode: false, // 201 first time; 409 if exists
    });
  }

  before(() => {
    signupViaApi();
  });

  it("logs in, stores token, and redirects to dashboard", () => {
    cy.visit("/login");

    // Fill login form (adjust selectors to your UI)
    cy.get('input[name="email"]').type(email);
    cy.get('input[name="password"]').type(password);
    cy.get('button[type="submit"]').click();

    // Assert redirect to dashboard
    cy.location("pathname", { timeout: 10000 }).should("eq", "/dashboard");

    // Assert token stored
    cy.window().then((win) => {
      const token = win.localStorage.getItem("auth_token");
      expect(token, "token stored in localStorage").to.be.a("string").and.not.empty;
    });
  });

  it("shows clear error when access_token missing", () => {
    // Intercept the login API to return a success without access_token
    const api = Cypress.env("REACT_APP_API_BASE_URL") || "http://localhost:3001";
    cy.intercept("POST", `${api}/auth/login`, {
      statusCode: 200,
      body: { token_type: "bearer" }, // deliberately missing access_token
    }).as("loginNoToken");

    cy.visit("/login");
    cy.get('input[name="email"]').type("someone@example.com");
    cy.get('input[name="password"]').type("SomePass123");
    cy.get('button[type="submit"]').click();

    // Expect a clear, user-facing error message
    cy.contains(/token was missing/i, { timeout: 10000 }).should("be.visible");
  });
});
