db.createUser({
  user: "atlas",
  pwd: process.env.MONGO_PASSWORD,
  roles: [
    {
      role: "dbOwner",
      db: "atlas"
    }
  ]
});

// Création des collections nécessaires
db = db.getSiblingDB('atlas');

db.createCollection("document_types");
db.createCollection("offers");
db.createCollection("company_profiles");
db.createCollection("company_user_profiles");
db.createCollection("candidate_profiles");
db.createCollection("plans");
db.createCollection("interviews");
db.createCollection("interview_records");
db.createCollection("interview_sheets");
db.createCollection("interview_questions");
db.createCollection("company_plan_subscriptions");
db.createCollection("admin_profiles");
// Création des index

