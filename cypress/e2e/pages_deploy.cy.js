describe('Production Pages - GitHub Events Dashboard', () => {
  it('loads and shows charts and table', () => {
    const base = Cypress.config('baseUrl') || 'https://sparesparrow.github.io/github-events';
    cy.visit(base);
    cy.contains('GitHub Events Monitor');
    cy.get('a[href="trending.json"]').should('exist');
    cy.request(base.replace(/\/$/, '') + '/trending.json').its('status').should('eq', 200);
  });
});


