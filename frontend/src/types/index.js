/**
 * @typedef {Object} User
 * @property {string} id
 * @property {string} firebase_uid
 * @property {string} email
 * @property {string} display_name
 * @property {string} photo_url
 * @property {boolean} is_admin
 * @property {number} daily_apply_cap
 */

/**
 * @typedef {Object} Job
 * @property {string} id
 * @property {string} title
 * @property {string} company
 * @property {string} location
 * @property {string} url
 * @property {string} description
 * @property {string[]} skills
 * @property {string} captured_at
 */

/**
 * @typedef {'planned'|'drafted'|'submitted'|'failed'|'needs_action'} ApplicationStatus
 */

/**
 * @typedef {Object} Application
 * @property {string} id
 * @property {string} job_id
 * @property {ApplicationStatus} status
 * @property {string|null} submitted_at
 * @property {string} notes
 * @property {string} created_at
 */

/**
 * @typedef {Object} Artifact
 * @property {string} id
 * @property {string} application_id
 * @property {'resume_pdf'|'cover_letter_pdf'|'resume_md'|'cover_letter_md'|'qa_json'|'screenshot'|'raw_job_json'|'imported_resume'} type
 * @property {string} cloudinary_url
 */

/**
 * @typedef {Object} Run
 * @property {string} id
 * @property {'scrape'|'compose'|'apply'} kind
 * @property {boolean|null} success
 * @property {string[]} log_lines
 * @property {string} started_at
 * @property {string|null} ended_at
 */

/**
 * @typedef {Object} Profile
 * @property {string} full_name
 * @property {string} location
 * @property {string} phone
 * @property {string} email
 * @property {string} linkedin_url
 * @property {string} portfolio_url
 * @property {string} summary
 * @property {string[]} skills
 * @property {string} experience_json
 * @property {string} education_json
 * @property {string} projects_json
 * @property {string} certifications_json
 */
