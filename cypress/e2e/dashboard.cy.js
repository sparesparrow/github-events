describe('GitHub Pages static dashboard', () => {
  it('renders metrics and trending table from static files', () => {
    cy.visit('/');
    cy.contains('GitHub Events Monitor');
    cy.contains('Static Data Mode');
    cy.get('#total-events').should('contain.text', '20');
    cy.get('#repos-tbody tr').should('have.length.at.least', 1);
  });
});
