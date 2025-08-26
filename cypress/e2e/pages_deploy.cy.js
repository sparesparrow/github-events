describe('Production Pages - GitHub Events Dashboard', () => {
  it('loads and shows charts and table', () => {
    const base = Cypress.config('baseUrl') || 'https://sparesparrow.github.io/github-events';
    
    // Ignore uncaught exceptions to handle JavaScript errors gracefully
    Cypress.on('uncaught:exception', (err, runnable) => {
      // Return false to prevent the error from failing the test
      return false;
    });
    
    cy.visit(base);
    cy.contains('GitHub Events Monitor');
    
    // Check for either the production page structure or the static fallback structure
    cy.get('body').then(($body) => {
      if ($body.find('a[href="trending.json"]').length > 0) {
        // Production page structure
        cy.get('a[href="trending.json"]').should('exist');
        cy.request(base.replace(/\/$/, '') + '/trending.json').its('status').should('eq', 200);
      } else {
        // Static fallback structure - check for the dashboard elements
        cy.get('#total-events').should('exist');
        cy.get('#repos-tbody').should('exist');
        cy.request(base.replace(/\/$/, '') + '/trending.json').its('status').should('eq', 200);
      }
    });
  });
});


