# Elevanalog Task Management Backend

This document outlines the Elevanalog backend, a focused application for managing tasks, designed for teams and individuals.

### 1. The Idea
The core idea is to build a robust, API-driven backend for a Software-as-a-Service (SaaS) productivity tool called "Elevanalog". This tool will help users manage tasks, track progress, collaborate within teams and organizations, and gain insights into their work patterns. The platform will be designed with a freemium model, offering core functionality for free and advanced features under a subscription plan.

### 2. Features
The backend is built with a modular, app-based architecture to support the following features:

*   **User & Authentication:** Secure user registration, login, password reset, and profile management.
*   **Organizations & Teams:** Users can create or join organizations and form teams within them. Access control will be based on roles (e.g., admin, member).
*   **Core Task Management:** Create, assign, update, and delete tasks. Users can add comments and upload file attachments to tasks.
*   **Accountability Tracking:** Features to set goals, define key results, and track progress against them on a per-task or per-project basis.

### 3. External APIs
While the project's main goal is to build our own robust REST API, it will integrate with external services for critical functions:

*   **File Storage:** A cloud storage solution like **Amazon S3** will be used in production to handle file uploads for task attachments, ensuring scalability and decoupling storage from the application server.
*   **Email Service:** A transactional email service like **SendGrid** or **Postmark** will be used to handle password resets and other essential emails reliably.

### 4. Models & API Endpoints
The architecture is centered around Django models and RESTful API endpoints.

**Key Models:**
*   `User`: Extends the default Django user.
*   `Organization`: The top-level entity.
*   `Team`: Belongs to an `Organization`.
*   `Task`: The core model, linked to a `Team`, an assignee (`User`), and a creator (`User`).
*   `TaskComment`, `TaskAttachment`: Linked to a `Task`.
*   `AccountabilityPartner`: Defines accountability relationships.

**Example API Endpoints:**
*   `POST /api/users/register/` - Create a new user.
*   `POST /api/users/token/` - Obtain an auth token.
*   `GET /api/organizations/` - List user's organizations.
*   `POST /api/organizations/` - Create a new organization.
*   `GET /api/tasks/` - List tasks for the user.
*   `POST /api/tasks/` - Create a new task.
*   `GET /api/tasks/{id}/` - Retrieve a specific task.
*   `POST /api/tasks/{id}/comments/` - Add a comment to a task.



### 6. Other Important Considerations

*   **Authentication Strategy:** Token-based authentication (e.g., JWT or DRF's built-in TokenAuthentication) will be used to secure the API.
*   **Testing:** A high level of test coverage is a priority. All business logic and API endpoints must have corresponding unit or integration tests.
*   **Scalability:** The architecture will be designed with scalability in mind, using Celery for asynchronous tasks (like sending emails) to avoid blocking web requests and using a scalable solution for file storage.
*   **Security:** Security best practices will be followed, including using environment variables for secrets, validating all user input, and implementing proper access controls.
