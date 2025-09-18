create or replace function get_uuid(user_email text)
    returns uuid as $$
declare
    user_id uuid;
begin
    -- strict will raise an error if 0 or more than 1 rows are returned.
    select id into strict user_id
    from auth.users
    where auth.users.email = user_email;

    return user_id;
end;
$$ language plpgsql;

-- To know the priority of the schemas. Where my commands get executed.
show search_path;