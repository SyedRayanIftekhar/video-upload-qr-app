{% extends "layout.html" %}

{% block content %}

<h2>Customers</h2>

<form method="POST" action="/create_customer">
    <input type="text" name="name" placeholder="Customer Name" required>
    <button type="submit">Add Customer</button>
</form>

<hr>

<table border="1" cellpadding="10">
    <tr>
        <th>ID</th>
        <th>Name</th>
        <th>QR Code</th>
        <th>Delete</th>
    </tr>

    {% for customer in customers %}
    <tr>
        <td>{{ customer[0] }}</td>
        <td>{{ customer[1] }}</td>
        <td>
            <a href="/download_qr/{{ customer[2] }}">Download QR</a>
        </td>
        <td>
            <form action="/delete_customer/{{ customer[0] }}" method="POST"
                  onsubmit="return confirm('Are you sure you want to delete this customer?');">
                <button type="submit">Delete</button>
            </form>
        </td>
    </tr>
    {% endfor %}
</table>

{% endblock %}
