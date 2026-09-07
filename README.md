# NexCart

A modern Django-based e-commerce marketplace for online shopping, product discovery, cart management, order processing, and seller operations.

<p align="center">
  <img src="https://img.shields.io/badge/Django-6.0.7-092E20?logo=django&logoColor=white" alt="Django 6.0.7" />
  <img src="https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white" alt="Python 3.11+" />
  <img src="https://img.shields.io/badge/Database-SQLite-003B57?logo=sqlite&logoColor=white" alt="SQLite" />
  <img src="https://img.shields.io/badge/Payments-Razorpay-0A0A0A?logo=razorpay&logoColor=white" alt="Razorpay" />
</p>

## Overview

NexCart is a full-stack online shopping project built with Django. It includes a storefront, product categories, shopping cart, checkout flow, order tracking, seller dashboard, and payment integration with Razorpay.

## Features

- Multi-category product catalog
- Product listing and search with filters
- Featured product showcase on the home page
- Shopping cart and checkout flow
- Razorpay payment integration
- Order history and order detail pages
- Seller dashboard and order management
- Admin-friendly Django structure
- Email verification and account authentication flow
- Responsive storefront UI

## Tech Stack

- Python
- Django 6.0.7
- SQLite database
- Razorpay API
- HTML, CSS, JavaScript
- Bootstrap-inspired custom templates

## Project Structure

```text
NexCart/
├── accounts/
├── cart/
├── config/
├── dashboard/
├── media/
├── orders/
├── payments/
├── products/
├── sellers/
├── static/
├── templates/
├── vendors/
├── wishlist/
├── .env.example
├── .gitignore
├── LICENSE
├── manage.py
├── README.md
├── requirements.txt
└── db.sqlite3
```

## Installation

1. Clone the repository

```bash
git clone https://github.com/your-username/NexCart.git
cd NexCart
```

2. Create and activate a virtual environment

```bash
python -m venv .venv
```

On Windows:

```bash
.venv\Scripts\activate
```

On macOS/Linux:

```bash
source .venv/bin/activate
```

3. Install dependencies

```bash
pip install -r requirements.txt
```

4. Configure environment variables

```bash
copy .env.example .env
```

Then update the values in `.env` with your own keys.

5. Run database migrations

```bash
python manage.py migrate
```

6. Create a superuser

```bash
python manage.py createsuperuser
```

7. Start the development server

```bash
python manage.py runserver
```

Open http://127.0.0.1:8000 in your browser.

## Environment Variables

Create a `.env` file using `.env.example` and set:

```env
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost
RAZORPAY_KEY_ID=your_razorpay_key_id
RAZORPAY_KEY_SECRET=your_razorpay_key_secret
```

## Screenshots

Add your project screenshots here for a more polished GitHub profile and repository presentation.

## Roadmap

- Improve product image gallery UI
- Add vendor onboarding flow
- Add analytics dashboard
- Improve mobile responsiveness
- Add tests for more payment workflows

## Contributing

Contributions are welcome. Please fork the repository, create a feature branch, and open a pull request.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Author

Built with Django for a complete digital storefront experience.
