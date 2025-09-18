describe('template spec', () => {

  const u0pwd = Cypress.env('U0PWD');

  // Runs before every it()
  beforeEach(() => {
    cy.task('runPgTAP');
  });

  // Runs once before the FIRST it()
  // before(() => {
  //   cy.task('runPgTAP');
  // });

  it('st-test', function() {
    cy.visit('http://localhost:8501/')
    cy.get('#text_input_1').click();
    cy.get('#text_input_1').clear();
    cy.get('#text_input_1').type('utest0@gmail.com');
    cy.get('#text_input_2').click();
    cy.get('#text_input_2').clear();
    cy.get('#text_input_2').type(u0pwd);
    cy.get('.element-container.st-key-FormSubmitter-login-Login [data-testid="stBaseButton-primaryFormSubmit"]').click();
    
    // Click fatture emesse tab - keep only as reference, not useful for this test.
    // Wait for the button to exist in the DOM
    cy.contains("button > div > p", "Fatture Emesse").should("exist");
    // Use force:true to avoid an error due to the way streamlit overlays elements on a page.
    cy.get("button > div > p").contains("Fatture Emesse").click({force: true});
    
    // Navigate to Uploader
    cy.get('[data-testid="stToolbar"] div:nth-child(1) > [aria-haspopup="true"] > .st-emotion-cache-13sb6qy > .st-emotion-cache-epvm6').click();
    cy.get('[data-testid="stTopNavLink"] .st-emotion-cache-awxmuf').click();
    
    // Upload invoice
    cy.get('[data-testid="stBaseButton-secondary"]').click(); // Browse File Button
    // cy.get('.st-emotion-cache-14bxo4c p').click();
    cy.get('input[type="file"]')
    .selectFile('cypress/fixtures/fatture_ricevute/test_IT01652880442_1fqw4.xml', { force: true });
    cy.get('.st-emotion-cache-14bxo4c p').click();
    cy.get('[data-testid="stAlertContainer"]').contains("Numero di fatture caricate correttamente: 1").click();
    
    // Navigate to Flussi di Cassa
    cy.get('[data-testid="stToolbar"] div:nth-child(2) > [aria-haspopup="true"] > .st-emotion-cache-13sb6qy > .st-emotion-cache-epvm6').click();
    cy.get('[data-testid="stTopNavLink"] .st-emotion-cache-1c4x2lm').click();

    // Trying to select the Passivi table but is difficult.
    cy.get('html > body > div:nth-of-type(1) > div:nth-of-type(1) > div:nth-of-type(1) > div > div > div > section > div:nth-of-type(1) > div > div:nth-of-type(4) > div > div > div:nth-of-type(2) > div:nth-of-type(1) > div > div > div:nth-of-type(1) > canvas:nth-of-type(1) > table > tbody')
        .find('tr')                       // Find all <tr> elements inside
        .should('have.length', 2);  // Assert that there are no external casse by expecting only two rows: Totali and Non specificato
    // Can I get stuff by ARIA role?
    // getByRole("row", {name: "Non specificato 0 0 0 0 0 0 0"})
  });
})