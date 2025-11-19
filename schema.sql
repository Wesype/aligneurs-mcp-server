-- Schema PostgreSQL pour les données d'activités aligneurs

-- Table principale des activités
CREATE TABLE IF NOT EXISTS activities (
    activity_id INTEGER PRIMARY KEY,
    activity_type VARCHAR(255) NOT NULL,
    description TEXT,
    date_activity TIMESTAMP,
    updated_at TIMESTAMP,
    destination_id INTEGER,
    source_id INTEGER,
    is_read BOOLEAN,
    patient_id INTEGER,
    is_finition BOOLEAN,
    treatment_id INTEGER,
    email_sent BOOLEAN,
    dentist_first_name VARCHAR(255),
    dentist_last_name VARCHAR(255),
    dentist_email VARCHAR(255),
    dentist_type VARCHAR(50),
    commercial_en_charge VARCHAR(255),
    commercial_name VARCHAR(255),
    suivi_portefeuille VARCHAR(255),
    id_invoice_pennylane VARCHAR(255),
    invoice_amount DECIMAL(10, 2),
    meta_data_object_name VARCHAR(100),
    number_of_aligners INTEGER,
    number_of_refinements INTEGER,
    number_of_retainers INTEGER
);

-- Table pour les AF Setups
CREATE TABLE IF NOT EXISTS af_setups (
    id INTEGER PRIMARY KEY,
    activity_id INTEGER REFERENCES activities(activity_id),
    lab INTEGER,
    treatment INTEGER,
    name VARCHAR(255),
    state VARCHAR(50),
    reason TEXT,
    lab_instruct TEXT,
    af_view TEXT,
    pdf_file TEXT,
    pdf_image_file TEXT,
    price DECIMAL(10, 2),
    discount_amount DECIMAL(10, 2),
    paid BOOLEAN,
    payment_status VARCHAR(50),
    pick_date TIMESTAMP,
    shipping_number VARCHAR(255),
    shipping_state VARCHAR(50),
    af_setup_date TIMESTAMP,
    updated_at TIMESTAMP,
    created_at TIMESTAMP,
    is_checked_by_lab BOOLEAN,
    is_checked_by_dentist BOOLEAN,
    is_price_changed BOOLEAN
);

-- Table pour les Treatments
CREATE TABLE IF NOT EXISTS treatments (
    id INTEGER PRIMARY KEY,
    activity_id INTEGER REFERENCES activities(activity_id),
    patient INTEGER,
    dentist INTEGER,
    state VARCHAR(50),
    phase INTEGER,
    is_finition BOOLEAN,
    parent_treatment_id INTEGER,
    finition_index INTEGER,
    note_in_production TEXT,
    note_in_production_updated_at TIMESTAMP,
    updated_at TIMESTAMP,
    created_at TIMESTAMP
);

-- Table pour les Invoices
CREATE TABLE IF NOT EXISTS invoices (
    id INTEGER PRIMARY KEY,
    activity_id INTEGER REFERENCES activities(activity_id),
    type VARCHAR(50),
    af_setup INTEGER,
    retainer INTEGER,
    title VARCHAR(255),
    due_date DATE,
    source_name VARCHAR(255),
    source_address TEXT,
    destination_name VARCHAR(255),
    destination_address TEXT,
    description TEXT,
    currency VARCHAR(10),
    quantity DECIMAL(10, 2),
    unit VARCHAR(50),
    unit_price DECIMAL(10, 2),
    tax DECIMAL(10, 2),
    amount DECIMAL(10, 2),
    aligner_org_price DECIMAL(10, 2),
    aligner_qta DECIMAL(10, 2),
    aligner_ttc DECIMAL(10, 2),
    aligner_pu_ht DECIMAL(10, 2),
    aligner_total_ht DECIMAL(10, 2),
    aligner_tva DECIMAL(10, 2),
    aligner_discount DECIMAL(10, 2),
    aligner_discount_rate DECIMAL(10, 2),
    aligner_discount_type VARCHAR(50),
    aligner_promo_code VARCHAR(100),
    aligner_prix_ht DECIMAL(10, 2),
    aligner_prix_ttc DECIMAL(10, 2),
    kit_10_qta DECIMAL(10, 2),
    kit_10_ttc DECIMAL(10, 2),
    kit_10_pu_ht DECIMAL(10, 2),
    kit_10_total_ht DECIMAL(10, 2),
    kit_10_tva DECIMAL(10, 2),
    kit_10_prix_ht DECIMAL(10, 2),
    kit_10_prix_ttc DECIMAL(10, 2),
    kit_16_qta DECIMAL(10, 2),
    kit_16_ttc DECIMAL(10, 2),
    kit_16_pu_ht DECIMAL(10, 2),
    kit_16_total_ht DECIMAL(10, 2),
    kit_16_tva DECIMAL(10, 2),
    kit_16_prix_ht DECIMAL(10, 2),
    kit_16_prix_ttc DECIMAL(10, 2),
    dm_qta DECIMAL(10, 2),
    dm_ttc DECIMAL(10, 2),
    dm_pu_ht DECIMAL(10, 2),
    dm_total_ht DECIMAL(10, 2),
    dm_tva DECIMAL(10, 2),
    dm_prix_ht DECIMAL(10, 2),
    dm_prix_ttc DECIMAL(10, 2),
    total_ht DECIMAL(10, 2),
    total_ttc DECIMAL(10, 2),
    total_discount DECIMAL(10, 2),
    payment_terms_days INTEGER,
    due_date_description TEXT,
    status VARCHAR(50),
    pdf_file TEXT,
    pdf_image_file TEXT,
    stripe_customer_id VARCHAR(255),
    updated_at TIMESTAMP,
    created_at TIMESTAMP
);

-- Table pour les Retainers
CREATE TABLE IF NOT EXISTS retainers (
    id INTEGER PRIMARY KEY,
    activity_id INTEGER REFERENCES activities(activity_id),
    patient INTEGER,
    treatment INTEGER,
    index INTEGER,
    state VARCHAR(50),
    pick_date TIMESTAMP,
    impression_type VARCHAR(50),
    impression_sub_type VARCHAR(50),
    shipping_number VARCHAR(255),
    shipping_state VARCHAR(50),
    dentist_id INTEGER,
    dentist_profile_id INTEGER,
    arcades_to_deal VARCHAR(50),
    number_of_pair VARCHAR(50),
    kit_balance_10 INTEGER,
    kit_balance_16 INTEGER,
    price DECIMAL(10, 2),
    order_status VARCHAR(50),
    is_checked_by_lab BOOLEAN,
    backup_state VARCHAR(50),
    updated_at TIMESTAMP,
    created_at TIMESTAMP
);

-- Table pour les Prescriptions
CREATE TABLE IF NOT EXISTS prescriptions (
    id INTEGER PRIMARY KEY,
    activity_id INTEGER REFERENCES activities(activity_id),
    treatment INTEGER,
    package INTEGER,
    package_type INTEGER,
    rejection_reason TEXT,
    clinic_objects JSONB,
    pdf_file TEXT,
    pdf_image_file TEXT,
    clinical_preference JSONB,
    pdf_file_clinic_preference TEXT,
    pdf_image_file_clinic_preference TEXT,
    lang_file VARCHAR(10),
    phase INTEGER,
    sub_phase INTEGER,
    updated_at TIMESTAMP,
    created_at TIMESTAMP
);

-- Index pour améliorer les performances
CREATE INDEX IF NOT EXISTS idx_activities_activity_type ON activities(activity_type);
CREATE INDEX IF NOT EXISTS idx_activities_patient_id ON activities(patient_id);
CREATE INDEX IF NOT EXISTS idx_activities_treatment_id ON activities(treatment_id);
CREATE INDEX IF NOT EXISTS idx_activities_date_activity ON activities(date_activity);
CREATE INDEX IF NOT EXISTS idx_af_setups_treatment ON af_setups(treatment);
CREATE INDEX IF NOT EXISTS idx_treatments_patient ON treatments(patient);
CREATE INDEX IF NOT EXISTS idx_invoices_af_setup ON invoices(af_setup);
CREATE INDEX IF NOT EXISTS idx_retainers_patient ON retainers(patient);
CREATE INDEX IF NOT EXISTS idx_prescriptions_treatment ON prescriptions(treatment);
